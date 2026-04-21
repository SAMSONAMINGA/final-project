/**
 * NextAuth.js Configuration
 * JWT-based session management wrapping backend /auth/token endpoint
 */

import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { api } from '@/lib/api';

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error('Invalid credentials');
        }

        try {
          // Call backend /auth/token endpoint
          const response = await api.login({
            email: credentials.email,
            password: credentials.password,
          });

          return {
            id: credentials.email,
            email: credentials.email,
            accessToken: response.access_token,
            refreshToken: response.refresh_token,
            // Note: isAdmin would be determined from JWT claims in real implementation
            isAdmin: false,
          };
        } catch (error) {
          throw new Error('Invalid email or password');
        }
      },
    }),
  ],
  pages: {
    signIn: '/login',
    error: '/login',
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        token.isAdmin = user.isAdmin;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.refreshToken = token.refreshToken as string;
      session.isAdmin = token.isAdmin as boolean;
      return session;
    },
  },
  session: {
    strategy: 'jwt',
    maxAge: 60 * 60, // 1 hour access token
  },
  jwt: {
    secret: process.env.NEXTAUTH_SECRET!,
    maxAge: 60 * 60,
  },
  secret: process.env.NEXTAUTH_SECRET!,
});

export { handler as GET, handler as POST };
