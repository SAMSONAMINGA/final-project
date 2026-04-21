/**
 * Barometer Repository
 * Business logic layer for sensor data management and submission
 * Objective: Offline resilience with exponential backoff retry
 */

package ke.floodguard.data

import android.content.Context
import ke.floodguard.data.local.ReadingDao
import ke.floodguard.data.local.ReadingEntity
import ke.floodguard.data.remote.BarometerPayload
import ke.floodguard.data.remote.FloodGuardApiService
import ke.floodguard.sensors.LocationCollector
import ke.floodguard.sensors.PressureCollector
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class BarometerRepository @Inject constructor(
    private val readingDao: ReadingDao,
    private val apiService: FloodGuardApiService,
    private val pressureCollector: PressureCollector,
    private val locationCollector: LocationCollector,
    private val context: Context
) {
    /**
     * Collect single barometer reading (pressure + GPS)
     * Synchronous to minimize wake lock duration (< 200ms)
     */
    suspend fun collectReading(): ReadingEntity? {
        val pressure = pressureCollector.readPressure() ?: return null
        val location = locationCollector.getLastLocation() ?: return null
        val deviceIdHash = getDeviceIdHash()
        val timestamp = System.currentTimeMillis().toString()

        val reading = ReadingEntity(
            deviceIdHash = deviceIdHash,
            pressureHpa = pressure.hpa,
            altitudeM = pressure.altitude,
            accuracy = location.accuracy,
            lat = location.lat,
            lng = location.lng,
            timestampDevice = java.time.Instant.now().toString()
        )

        // Store locally for offline queue
        val id = readingDao.insert(reading)
        return reading.copy(id = id)
    }

    /**
     * Attempt to upload all pending readings
     * Exponential backoff: 1s, 2s, 4s, 8s, ... up to max_attempts (3)
     */
    suspend fun uploadPendingReadings() {
        val pending = readingDao.getPendingReadings()
        for (reading in pending) {
            uploadWithRetry(reading)
        }
    }

    private suspend fun uploadWithRetry(reading: ReadingEntity) {
        val maxAttempts = 3
        var attempts = reading.uploadAttempts

        while (attempts < maxAttempts) {
            try {
                // Exponential backoff delay (1s * 2^attempts)
                if (attempts > 0) {
                    val delayMs = (1000L * Math.pow(2.0, (attempts - 1).toDouble())).toLong()
                    kotlinx.coroutines.delay(delayMs)
                }

                val payload = BarometerPayload(
                    deviceIdHash = reading.deviceIdHash,
                    pressureHpa = reading.pressureHpa,
                    altitudeM = reading.altitudeM,
                    accuracy = reading.accuracy,
                    lat = reading.lat,
                    lng = reading.lng,
                    timestampDevice = reading.timestampDevice
                )

                apiService.submitBarometerReading(payload)

                // Mark as uploaded
                readingDao.update(reading.copy(uploaded = true, uploadAttempts = 0))
                return
            } catch (e: Exception) {
                attempts++
                if (attempts >= maxAttempts) {
                    // Max retries exceeded — keep in queue for next batch
                    readingDao.update(reading.copy(uploadAttempts = attempts))
                    return
                }
            }
        }
    }

    fun getPendingReadingsCountFlow(): Flow<Int> {
        return readingDao.getPendingReadingsCount()
    }

    suspend fun getReadingsCountToday(): Int {
        return readingDao.getReadingsCountToday()
    }

    private fun getDeviceIdHash(): String {
        // Hash Android device ID with SHA-256 (privacy — never send raw ID)
        val deviceId = android.provider.Settings.Secure.getString(
            context.contentResolver,
            android.provider.Settings.Secure.ANDROID_ID
        ) ?: "unknown"

        return java.security.MessageDigest.getInstance("SHA-256")
            .digest(deviceId.toByteArray())
            .joinToString("") { "%02x".format(it) }
    }
}
