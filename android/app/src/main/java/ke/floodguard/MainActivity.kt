/**
 * Main Activity
 * Jetpack Compose entry point with tab navigation
 */

package ke.floodguard

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import dagger.hilt.android.AndroidEntryPoint
import ke.floodguard.ui.screens.AlertsScreen
import ke.floodguard.ui.screens.OnboardingScreen
import ke.floodguard.ui.screens.RiskScreen
import ke.floodguard.ui.screens.StatusScreen
import ke.floodguard.ui.theme.FloodGuardTheme
import ke.floodguard.workers.BarometerUploadWorker
import java.util.concurrent.TimeUnit

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            FloodGuardTheme {
                MainApp()
            }
        }

        // Schedule WorkManager for 5-min barometer collection
        scheduleBarometerWorker()
    }

    private fun scheduleBarometerWorker() {
        val barometerWork = PeriodicWorkRequestBuilder<BarometerUploadWorker>(
            5, TimeUnit.MINUTES,
            5, TimeUnit.MINUTES // FlexInterval
        ).addTag(BarometerUploadWorker.WORK_TAG).build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            BarometerUploadWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            barometerWork
        )
    }
}

@Composable
fun MainApp() {
    var currentTab by remember { mutableIntStateOf(0) }
    var showOnboarding by remember { mutableIntStateOf(1) } // 1=show, 0=skip

    if (showOnboarding == 1) {
        OnboardingScreen(onComplete = { showOnboarding = 0 })
    } else {
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            topBar = {
                TabRow(selectedTabIndex = currentTab) {
                    Tab(
                        selected = currentTab == 0,
                        onClick = { currentTab = 0 },
                        text = { Text("Status") }
                    )
                    Tab(
                        selected = currentTab == 1,
                        onClick = { currentTab = 1 },
                        text = { Text("My Risk") }
                    )
                    Tab(
                        selected = currentTab == 2,
                        onClick = { currentTab = 2 },
                        text = { Text("Alerts") }
                    )
                }
            }
        ) { padding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
            ) {
                when (currentTab) {
                    0 -> StatusScreen()
                    1 -> RiskScreen()
                    2 -> AlertsScreen()
                }
            }
        }
    }
}
