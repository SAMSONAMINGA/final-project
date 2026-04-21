/**
 * Pressure Sensor Collector
 * Barometer reading via SensorManager (TYPE_PRESSURE)
 * Objective: Collect baseline pressure for rainfall fusion (Overeem et al. 2019)
 */

package ke.floodguard.sensors

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import kotlin.math.pow

class PressureCollector @Inject constructor(
    @ApplicationContext private val context: Context
) : SensorEventListener {
    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val pressureSensor = sensorManager.getDefaultSensor(Sensor.TYPE_PRESSURE)
    private var lastPressureReading: PressureData? = null

    data class PressureData(
        val hpa: Float, // Hectopascals
        val altitude: Float // Estimated altitude (meters)
    )

    /**
     * Read pressure synchronously (blocking until reading available)
     * Objective: < 200ms wake lock for minimal battery impact
     */
    fun readPressure(): PressureData? {
        if (pressureSensor == null) return null

        sensorManager.registerListener(this, pressureSensor, SensorManager.SENSOR_DELAY_FASTEST)

        // Wait up to 500ms for reading
        val startTime = System.currentTimeMillis()
        while (System.currentTimeMillis() - startTime < 500) {
            if (lastPressureReading != null) {
                val reading = lastPressureReading
                sensorManager.unregisterListener(this)
                return reading
            }
            Thread.sleep(10)
        }

        sensorManager.unregisterListener(this)
        return lastPressureReading
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type == Sensor.TYPE_PRESSURE) {
            val pressureHpa = event.values[0]
            // Calculate altitude from barometric formula (simplified)
            // h = 44330 * (1 - (P/P0)^(1/5.255))
            val altitude = 44330 * (1 - (pressureHpa / 1013.25).pow(1 / 5.255f))
            lastPressureReading = PressureData(pressureHpa, altitude)
        }
    }

    override fun onAccuracyChanged(sensor: Sensor, accuracy: Int) {}
}
