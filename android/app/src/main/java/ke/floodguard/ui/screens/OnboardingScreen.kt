/**
 * Onboarding Screen
 * Privacy explanation, consent, and language selection
 */

package ke.floodguard.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun OnboardingScreen(onComplete: () -> Unit) {
    var consentGiven by remember { mutableStateOf(false) }
    var selectedLanguage by remember { mutableStateOf("en") }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            "Welcome to FloodGuard KE",
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.onSurface
        )

        // Privacy explanation
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF1F2937), shape = MaterialTheme.shapes.medium)
                .padding(16.dp)
        ) {
            Column(
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    "What We Collect",
                    style = MaterialTheme.typography.titleSmall,
                    color = Color(0xFFD4AF37)
                )
                Text(
                    "✓ Barometer pressure readings\n✓ GPS location (county-level)",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFF10B981)
                )

                Text(
                    "What We Don't Collect",
                    style = MaterialTheme.typography.titleSmall,
                    color = Color(0xFFEF4444),
                    modifier = Modifier.padding(top = 8.dp)
                )
                Text(
                    "✗ Your name or phone number\n✗ Contacts or personal information\n✗ Call/message history",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFFF3F4F6)
                )
            }
        }

        // Language selection
        Column(
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                "Language",
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onSurface
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                listOf("English" to "en", "Swahili" to "sw", "Sheng" to "sheng").forEach { (name, code) ->
                    OutlinedButton(
                        onClick = { selectedLanguage = code },
                        modifier = Modifier
                            .weight(1f)
                            .background(
                                if (selectedLanguage == code) Color(0xFFD4AF37) else Color.Transparent,
                                shape = MaterialTheme.shapes.small
                            )
                    ) {
                        Text(name, color = if (selectedLanguage == code) Color.Black else Color.White)
                    }
                }
            }
        }

        // Consent checkbox
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Checkbox(
                checked = consentGiven,
                onCheckedChange = { consentGiven = it }
            )
            Text(
                "I consent to FloodGuard collecting pressure and location data to improve flood early warning",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface
            )
        }

        // Action buttons
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Button(
                onClick = { if (consentGiven) onComplete() },
                enabled = consentGiven,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Agree & Continue")
            }

            OutlinedButton(
                onClick = { onComplete() }, // Skip for demo
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Continue Without")
            }
        }
    }
}
