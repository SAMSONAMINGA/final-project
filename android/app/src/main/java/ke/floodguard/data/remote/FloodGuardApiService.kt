/**
 * FloodGuard API Service
 * Retrofit interface for backend integration
 */

package ke.floodguard.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.POST

interface FloodGuardApiService {
    /**
     * POST /ingest/barometer
     * Submit barometer reading from Android device
     * Rate limit: 60 req/min from single device
     */
    @POST("/ingest/barometer")
    suspend fun submitBarometerReading(@Body payload: BarometerPayload): SubmitResponse

    /**
     * GET /risk/{county_code}
     * Fetch latest risk assessment (node-level with SHAP explanations)
     */
    @GET("/risk/{county_code}")
    suspend fun getRiskForCounty(@Path("county_code") countyCode: String): RiskResponse

    data class SubmitResponse(val status: String, val message: String? = null)

    data class RiskResponse(
        val county_code: String,
        val county_name: String,
        val valid_time: String,
        val county_risk_score: Float,
        val risk_level: String, // Low, Medium, High, Critical
        val nodes: List<RiskNode>
    )

    data class RiskNode(
        val node_id: String,
        val lat: Double,
        val lng: Double,
        val risk_score: Float,
        val depth_cm: Int,
        val shap_top3: List<ShapFactor>,
        val alert_message_en: String,
        val alert_message_sw: String
    )

    data class ShapFactor(
        val factor: String,
        val contribution: Float
    )
}
