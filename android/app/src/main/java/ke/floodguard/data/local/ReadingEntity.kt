/**
 * Room Database Entity: Barometer Reading
 * Local queue for offline resilience (retry on reconnection)
 */

package ke.floodguard.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "barometer_readings")
data class ReadingEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0L,
    val deviceIdHash: String, // Device ID (SHA-256 hashed on-device)
    val pressureHpa: Float,
    val altitudeM: Float,
    val accuracy: Int,
    val lat: Double,
    val lng: Double,
    val timestampDevice: String, // ISO 8601
    val uploaded: Boolean = false, // Track upload status
    val uploadAttempts: Int = 0, // Retry counter
    val createdAtLocal: Long = System.currentTimeMillis() // Local timestamp
)
