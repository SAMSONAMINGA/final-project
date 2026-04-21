/**
 * Barometer Background Worker
 * WorkManager PeriodicWorkRequest (5 min interval)
 * Objective: Collect & submit barometer readings with zero battery impact (< 0.5% per day)
 */

package ke.floodguard.workers

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import dagger.hilt.android.qualifiers.ApplicationContext
import ke.floodguard.data.BarometerRepository
import javax.inject.Inject

class BarometerUploadWorker(
    @ApplicationContext context: Context,
    params: WorkerParameters,
    private val repository: BarometerRepository
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            // Collect single barometer reading (< 200ms wake lock)
            repository.collectReading()

            // Attempt to upload all pending readings (with backoff)
            repository.uploadPendingReadings()

            Result.success()
        } catch (e: Exception) {
            // Exponential backoff retry (WorkManager handles retries)
            Result.retry()
        }
    }

    companion object {
        const val WORK_TAG = "barometer_upload"
        const val WORK_NAME = "barometer_periodic"
    }
}

/**
 * Worker Factory for Hilt Dependency Injection
 */
@Inject
class BarometerWorkerFactory(
    private val repository: BarometerRepository
) {
    fun createWorker(
        context: Context,
        params: WorkerParameters
    ): BarometerUploadWorker {
        return BarometerUploadWorker(context, params, repository)
    }
}
