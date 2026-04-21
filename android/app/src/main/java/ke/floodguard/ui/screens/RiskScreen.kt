/**
 * Risk Screen
 * Displays local county risk level with SHAP factor explanations
 */

package ke.floodguard.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun RiskScreen() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            "My Area Risk",
            style = MaterialTheme.typography.headlineLarge,
            color = MaterialTheme.colorScheme.onSurface
        )

        // Risk gauge (0-100%)
        RiskGaugeWidget(riskScore = 45)

        // SHAP factors
        Text(
            "Top Contributing Factors",
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.onSurface
        )

        ShapFactorItem("Barometer pressure drop", 35)
        ShapFactorItem("High rainfall last 6h", 28)
        ShapFactorItem("River upstream gauge levels", 20)
    }
}

@Composable
fun RiskGaugeWidget(riskScore: Int) {
    val colour = when {
        riskScore < 25 -> Color(0xFF10B981)
        riskScore < 50 -> Color(0xFFF59E0B)
        riskScore < 75 -> Color(0xFFEF4444)
        else -> Color(0xFF7F1D1D)
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                color = MaterialTheme.colorScheme.surface,
                shape = MaterialTheme.shapes.medium
            )
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Risk Score", style = MaterialTheme.typography.bodySmall)
            Text("$riskScore%", style = MaterialTheme.typography.headlineSmall, color = colour)
        }

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .background(Color(0xFF4B5563), shape = MaterialTheme.shapes.small)
                .padding(top = 8.dp)
        )

        Box(
            modifier = Modifier
                .fillMaxWidth(fraction = riskScore / 100f)
                .height(8.dp)
                .background(colour, shape = MaterialTheme.shapes.small)
        )
    }
}

@Composable
fun ShapFactorItem(factor: String, contribution: Int) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF1F2937), shape = MaterialTheme.shapes.small)
            .padding(12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(factor, style = MaterialTheme.typography.bodySmall)
        Text("${contribution}%", style = MaterialTheme.typography.labelSmall, color = Color(0xFFD4AF37))
    }
}
