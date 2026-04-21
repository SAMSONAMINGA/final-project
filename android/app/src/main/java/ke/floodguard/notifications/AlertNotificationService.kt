/**
 * Alert Notification Service
 * FCM message handler for push notifications
 * Objective: Deliver HIGH/CRITICAL risk alerts in real-time
 */

package ke.floodguard.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import ke.floodguard.MainActivity
import ke.floodguard.R

class AlertNotificationService : FirebaseMessagingService() {

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        // Handle FCM message
        val data = remoteMessage.data
        val title = data["title"] ?: "FloodGuard Alert"
        val message = data["message"] ?: "Flood alert received"
        val countyCode = data["county_code"]
        val riskLevel = data["risk_level"] ?: "High"

        // Show notification
        showNotification(title, message, countyCode, riskLevel)
    }

    private fun showNotification(
        title: String,
        message: String,
        countyCode: String?,
        riskLevel: String
    ) {
        val notificationManager =
            getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        // Create notification channel (Android 8+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "FloodGuard Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Real-time flood risk notifications"
                enableVibration(true)
                enableLights(true)
            }
            notificationManager.createNotificationChannel(channel)
        }

        // Deep link intent to alerts screen
        val intent = Intent(this, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            data = android.net.Uri.parse("floodguard://alerts?county=$countyCode")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }

        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // Colour code by risk level
        val colour = when (riskLevel) {
            "Critical" -> 0xFF7F1D1D // Dark red
            "High" -> 0xFFEF4444 // Red
            "Medium" -> 0xFFF59E0B // Amber
            else -> 0xFF10B981 // Green
        }

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification) // Requires drawable resource
            .setContentTitle(title)
            .setContentText(message)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .setColor(colour.toInt())
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setStyle(
                NotificationCompat.BigTextStyle()
                    .bigText(message)
            )
            .build()

        notificationManager.notify(NOTIFICATION_ID, notification)
    }

    companion object {
        private const val CHANNEL_ID = "floodguard_alerts"
        private const val NOTIFICATION_ID = 1
    }
}
