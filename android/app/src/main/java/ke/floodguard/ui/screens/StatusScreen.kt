/**
 * Status Screen
 * Shows "Contributing to FloodGuard KE" indicator, current reading, upload count
 */

package ke.floodguard.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Icon
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ke.floodguard.data.BarometerRepository
import ke.floodguard.sensors.LocationCollector
import ke.floodguard.sensors.PressureCollector
import javax.inject.Inject

@Composable
fun StatusScreen() {
    var pressure by remember { mutableStateOf<Float?>(null) }
    var location by remember { mutableStateOf<String?>(null) }
    var uploadCount by remember { mutableStateOf(0) }

    // TODO: Inject ViewModel instead of repository directly
    // For demo, we show placeholder values

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Active status indicator
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    color = Color(0xFF10B981).copy(alpha = 0.1f),
                    shape = MaterialTheme.shapes.medium
                )
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Icon(
                imageVector = Icons.Default.CheckCircle,
                contentDescription = "Active",
                tint = Color(0xFF10B981),
                modifier = Modifier.size(24.dp)
            )
            Column {
                Text(
                    "Contributing to FloodGuard KE",
                    style = MaterialTheme.typography.titleSmall,
                    color = Color(0xFF10B981)
                )
                Text(
                    "Your barometer readings help save lives",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFFAEAEAE)
                )
            }
        }

        // Current readings
        StatCard("Current Pressure", "${pressure ?: "--"} hPa")
        StatCard("GPS Coordinates", location ?: "Loading...")
        StatCard("Uploads Today", "$uploadCount readings")
        StatCard("Battery Impact", "< 0.5% per day")
    }
}

@Composable
fun StatCard(label: String, value: String) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                color = MaterialTheme.colorScheme.surface,
                shape = MaterialTheme.shapes.medium
            )
            .padding(16.dp)
    ) {
        Column {
            Text(
                label,
                style = MaterialTheme.typography.labelSmall,
                color = Color(0xFF9CA3AF)
            )
            Text(
                value,
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}
