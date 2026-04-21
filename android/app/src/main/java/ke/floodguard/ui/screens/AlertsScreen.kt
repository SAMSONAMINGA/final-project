/**
 * Alerts Screen
 * Displays push notifications & SMS alerts received
 */

package ke.floodguard.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun AlertsScreen() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            "Recent Alerts",
            style = MaterialTheme.typography.headlineLarge,
            color = MaterialTheme.colorScheme.onSurface
        )

        // Sample alert items
        val alerts = listOf(
            AlertItem("HIGH risk in Tana River", "2 hours ago", "HIGH"),
            AlertItem("Update: Risk downgraded to MEDIUM", "5 hours ago", "MEDIUM")
        )

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(alerts) { alert ->
                AlertItemCard(alert)
            }
        }

        // Test alert button (admin only)
        Button(
            onClick = { /* Send test alert */ },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Send Test Alert (Admin)")
        }
    }
}

data class AlertItem(
    val message: String,
    val timestamp: String,
    val riskLevel: String
)

@Composable
fun AlertItemCard(alert: AlertItem) {
    val bgColour = when (alert.riskLevel) {
        "CRITICAL" -> Color(0xFF7F1D1D).copy(alpha = 0.2f)
        "HIGH" -> Color(0xFFEF4444).copy(alpha = 0.2f)
        "MEDIUM" -> Color(0xFFF59E0B).copy(alpha = 0.2f)
        else -> Color(0xFF10B981).copy(alpha = 0.2f)
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(bgColour, shape = MaterialTheme.shapes.medium)
            .padding(12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column {
            Text(alert.message, style = MaterialTheme.typography.bodySmall)
            Text(alert.timestamp, style = MaterialTheme.typography.labelSmall, color = Color(0xFF9CA3AF))
        }
        Text(alert.riskLevel, style = MaterialTheme.typography.labelSmall, color = Color(0xFFFFB700))
    }
}
