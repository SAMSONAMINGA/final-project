/**
 * FloodGuard Theme
 * Jetpack Compose Material Design 3 theme (dark mode)
 * Kenyan colour palette for accessibility
 */

package ke.floodguard.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Kenyan colour palette
private val MaasaiRed = Color(0xFF8B0000)
private val SavannaGold = Color(0xFFD4AF37)
private val KenyaGreen = Color(0xFF39A900)
private val RiskLow = Color(0xFF10B981)
private val RiskMedium = Color(0xFFF59E0B)
private val RiskHigh = Color(0xFFEF4444)
private val RiskCritical = Color(0xFF7F1D1D)

private val DarkColorScheme = darkColorScheme(
    primary = SavannaGold,
    secondary = KenyaGreen,
    tertiary = MaasaiRed,
    background = Color(0xFF111827),
    surface = Color(0xFF1F2937),
    onBackground = Color(0xFFF3F4F6),
    onSurface = Color(0xFFF3F4F6),
)

@Composable
fun FloodGuardTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        typography = androidx.compose.material3.Typography(),
        content = content
    )
}
