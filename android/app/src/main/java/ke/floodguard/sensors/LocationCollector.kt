/**
 * Location Collector
 * GPS via FusedLocationProviderClient for high-accuracy placement
 * Objective: Enable county-level spatial lookup in backend (PostGIS ST_Contains)
 */

package ke.floodguard.sensors

import android.content.Context
import android.location.Location
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.tasks.await
import javax.inject.Inject

class LocationCollector @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val fusedLocationClient: FusedLocationProviderClient =
        LocationServices.getFusedLocationProviderClient(context)

    data class LocationData(
        val lat: Double,
        val lng: Double,
        val accuracy: Int
    )

    /**
     * Get last known location (cached, fastest)
     * Fallback to network/fused provider if GPS unavailable
     */
    suspend fun getLastLocation(): LocationData? {
        val location = try {
            fusedLocationClient.lastLocation.await()
        } catch (e: Exception) {
            // Permission denied or provider unavailable
            return null
        }

        return location?.let {
            LocationData(
                lat = it.latitude,
                lng = it.longitude,
                accuracy = it.accuracy.toInt()
            )
        }
    }

    /**
     * Request fresh location update (higher accuracy, longer latency)
     * Used for initial calibration, not every reading
     */
    suspend fun getCurrentLocationFresh(): LocationData? {
        return try {
            val location = fusedLocationClient.getCurrentLocation(
                Priority.PRIORITY_HIGH_ACCURACY,
                null // CancellationToken not available in suspend context
            ).await()

            location?.let {
                LocationData(
                    lat = it.latitude,
                    lng = it.longitude,
                    accuracy = it.accuracy.toInt()
                )
            }
        } catch (e: Exception) {
            null
        }
    }
}
