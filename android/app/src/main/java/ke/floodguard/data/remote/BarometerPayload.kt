/**
 * Barometer Payload Data Class
 * ~180 bytes JSON for sensor readings sent to /ingest/barometer
 */

package ke.floodguard.data.remote

import com.google.gson.annotations.SerializedName

data class BarometerPayload(
    @SerializedName("device_id_hash")
    val deviceIdHash: String, // SHA-256 hashed Android device ID (never raw)
    @SerializedName("pressure_hpa")
    val pressureHpa: Float, // Barometer reading in hPa
    @SerializedName("altitude_m")
    val altitudeM: Float, // Estimated altitude from pressure
    @SerializedName("accuracy")
    val accuracy: Int, // Location accuracy in meters
    @SerializedName("lat")
    val lat: Double, // GPS latitude
    @SerializedName("lng")
    val lng: Double, // GPS longitude
    @SerializedName("timestamp_device")
    val timestampDevice: String // ISO 8601 device timestamp
)
