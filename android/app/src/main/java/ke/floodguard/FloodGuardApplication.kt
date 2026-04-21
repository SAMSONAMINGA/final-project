/**
 * FloodGuard Application Class
 * Hilt initialization and global setup
 */

package ke.floodguard

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class FloodGuardApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // Hilt initialization happens automatically via @HiltAndroidApp annotation
        // WorkManager scheduling for barometer ingestion happens in MainActivity
    }
}
