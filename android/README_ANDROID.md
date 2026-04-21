# FloodGuard KE Android Documentation

## Overview

Production-grade Kotlin Android app (API 26+) for nationwide Kenya flood early warning system. Collects barometer + GPS readings via background WorkManager service and displays local risk assessment with push notifications.

**Objective**: Enable 1000s of volunteer citizens to contribute pressure readings for rainfall fusion, with <0.5% daily battery impact.

## Architecture

### Tech Stack
- **Language**: Kotlin
- **Minimum SDK**: API 26 (Android 8.0)
- **Target SDK**: API 34 (Android 14)
- **UI Framework**: Jetpack Compose (Material Design 3)
- **Navigation**: Jetpack Navigation Compose
- **Dependency Injection**: Hilt 2.48
- **Database**: Room (local queue for offline resilience)
- **Networking**: Retrofit 2 + OkHttp + Gson
- **Background Work**: WorkManager (PeriodicWorkRequest every 5 min)
- **Location**: Google Play Services (FusedLocationProvider)
- **Notifications**: Firebase Cloud Messaging (FCM)
- **Preferences**: Jetpack DataStore
- **Sensors**: Android SensorManager (TYPE_PRESSURE)

### App Structure

```
MainActivity (Jetpack Compose)
├── OnboardingScreen (consent + language)
├── StatusScreen (active status + readings)
├── RiskScreen (county risk + SHAP factors)
└── AlertsScreen (SMS/USSD history)

Background Services
├── BarometerUploadWorker (5-min periodic)
├── PressureCollector (barometer sensor)
├── LocationCollector (GPS via FusedLocationProvider)
└── AlertNotificationService (FCM handler)

Data Layer
├── BarometerRepository (business logic)
├── ReadingDao (Room DAO)
├── ReadingEntity (offline queue table)
└── FloodGuardApiService (Retrofit client)
```

### Screens

#### OnboardingScreen
- Privacy explanation: **Collected**: pressure + GPS | **Not collected**: name, phone, contacts
- Language selector: English / Swahili / Sheng
- Consent toggle (required to enable WorkManager)
- Skip option (for demo)

#### StatusScreen (Tab 0)
- "Contributing to FloodGuard KE" indicator
- Current pressure reading (hPa)
- GPS coordinates (lat, lng)
- Upload count today
- Battery impact badge (< 0.5% per day)

#### RiskScreen (Tab 1)
- County risk level from local backend cache
- Risk gauge (0-100% visual)
- Top 3 SHAP factors (plain English + Swahili)
- Factor contribution percentages

#### AlertsScreen (Tab 2)
- List of received SMS/USSD alerts (timestamp)
- Risk level badge per alert
- Test alert button (admin-only)
- Deep link support (floodguard://alerts)

## Background Service (WorkManager)

### Implementation

```kotlin
// Scheduled in MainActivity.onCreate()
val barometerWork = PeriodicWorkRequestBuilder<BarometerUploadWorker>(
    5, TimeUnit.MINUTES,
    5, TimeUnit.MINUTES  // FlexInterval for battery optimization
).addTag("barometer_upload").build()

WorkManager.getInstance(context).enqueueUniquePeriodicWork(
    "barometer_periodic",
    ExistingPeriodicWorkPolicy.KEEP,
    barometerWork
)
```

### Sensor Collection

**BarometerUploadWorker** executes every 5 minutes:
1. **Collect pressure** (< 100ms wake lock)
   - SensorManager.TYPE_PRESSURE
   - Calculate altitude via barometric formula
   - Release sensor listener immediately

2. **Collect location** (< 100ms wake lock)
   - FusedLocationProvider.getLastLocation() [cached]
   - Falls back to network/fused if GPS unavailable

3. **Hash device ID** (SHA-256 on-device)
   - Never send raw Android device ID
   - Maintains privacy while enabling volunteer tracking

4. **Store locally** (Room database)
   - Queue for offline resilience
   - Track upload attempts

5. **Upload batch**
   - POST to `/ingest/barometer` (180 bytes each)
   - Exponential backoff retry (1s, 2s, 4s, max 3 attempts)
   - Mark as uploaded on success
   - Retain on failure for next cycle

### Battery Impact

- **Wake lock duration**: < 200ms per reading
- **Frequency**: Every 5 minutes
- **Monthly impact**: 
  - 288 readings (5-min interval × 24h × 30 days)
  - ~200ms × 288 = ~57 seconds = 0.002% CPU time
- **Network**: ~180 bytes × 288 = ~52 KB/month (negligible)
- **Result**: < 0.5% battery per day (typical phone has 4000+ mAh)

## Data Models

### BarometerPayload (JSON to backend)
```json
{
  "device_id_hash": "6f8db008...",  // SHA-256 hashed
  "pressure_hpa": 1013.25,
  "altitude_m": 0.0,
  "accuracy": 5,
  "lat": -1.28,
  "lng": 36.82,
  "timestamp_device": "2026-04-20T14:35:00Z"
}
```

### ReadingEntity (Room local table)
- `id`: Auto-increment primary key
- `deviceIdHash`: SHA-256 hash
- `pressure*`, `altitude*`, `accuracy*`, `lat*`, `lng*`
- `uploaded`: Boolean (track sync status)
- `uploadAttempts`: Int (retry counter)
- `createdAtLocal`: Long (device time)

## API Integration

### Retrofit Service

```kotlin
interface FloodGuardApiService {
    @POST("/ingest/barometer")
    suspend fun submitBarometerReading(@Body payload: BarometerPayload): SubmitResponse

    @GET("/risk/{county_code}")
    suspend fun getRiskForCounty(@Path("county_code") countyCode: String): RiskResponse
}
```

### FCM Integration

**AlertNotificationService** (FCM message handler):
- Receives push from Firebase Cloud Messaging
- Colour-codes notification by risk level (green/amber/red/dark-red)
- Deep link to `floodguard://alerts?county=KEN01`
- Shows in notification tray with vibration + light

```json
// Example FCM payload
{
  "title": "HIGH Risk Alert",
  "message": "Tana River: 70% flood risk",
  "county_code": "KEN04",
  "risk_level": "High"
}
```

## Privacy & Security

### On-Device Privacy
✅ Device ID hashed (SHA-256) before upload
✅ No name, phone, contacts, call history collected
✅ Location only used for county-level lookup (≤5km accuracy)
✅ All user data encrypted in Room database (AndroidX Security)
✅ HTTPS only (OkHttp TLS 1.2+)

### Consent Flow
1. OnboardingScreen explains data usage
2. User explicitly toggles consent
3. WorkManager **only starts after consent**
4. Revokable via Settings (uncheck "Enable FloodGuard")

## Permissions

### Required
- `INTERNET`: API communication
- `ACCESS_FINE_LOCATION`: GPS (FusedLocationProvider)
- `ACCESS_COARSE_LOCATION`: Fallback network location
- `RECEIVE_BOOT_COMPLETED`: Reschedule WorkManager after reboot
- `WAKE_LOCK`: Sensor readings (short duration)
- `POST_NOTIFICATIONS`: Android 13+ FCM notifications

### Runtime Permissions
- Location permissions requested at runtime (Android 6+)
- Graceful degradation if denied (use cached location)

## Offline Resilience

**Room local queue** enables:
- Submit readings while offline
- Auto-upload when connectivity restored
- Exponential backoff (1s → 2s → 4s)
- Persist up to 1000 readings locally
- Periodic cleanup of uploaded readings

## Hilt Dependency Injection

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides
    @Singleton
    fun provideFloodGuardApiService(okHttpClient: OkHttpClient): FloodGuardApiService { ... }
    
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase { ... }
    
    @Provides
    @Singleton
    fun providePressureCollector(@ApplicationContext context: Context): PressureCollector { ... }
    // ... more providers
}

// Usage in any class:
@Inject lateinit var repository: BarometerRepository
```

## Jetpack Compose UI

### Material Design 3 Dark Theme
- Primary: Savanna Gold (#D4AF37)
- Secondary: Kenya Green (#39A900)
- Tertiary: Maasai Red (#8B0000)
- Surface: Dark gray (#1F2937)

### Accessibility
✅ Minimum 18sp touch targets
✅ Sufficient colour contrast
✅ Semantic composables (@Composable functions)
✅ Content descriptions for images

### Screens (Tab Navigation)
```kotlin
Scaffold(
    topBar = { TabRow(...) }
) {
    when (currentTab) {
        0 -> StatusScreen()
        1 -> RiskScreen()
        2 -> AlertsScreen()
    }
}
```

## Development

### Build & Run
```bash
# Build APK
./gradlew build

# Install to emulator
./gradlew installDebug

# Run with logging
adb logcat | grep "floodguard"
```

### Emulator Setup
- Minimum API 26 (Android 8.0)
- Google APIs image (for Google Play Services + FCM)
- Extended controls → Virtual sensors → Simulate pressure changes

### Testing
```bash
# Unit tests
./gradlew test

# Instrumented tests (on emulator)
./gradlew connectedAndroidTest
```

## Deployment

### Release Build
```bash
./gradlew bundleRelease  # Create AAB for Play Store
./gradlew assembleRelease  # Create APK
```

### Google Play Store
1. Sign APK with release keystore
2. Create app listing
3. Upload to Play Store Console
4. Set up Firebase Cloud Messaging credentials
5. Configure backend API URL (BuildConfig.API_URL)

### Analytics
- Firebase Analytics integrated
- Track: app opens, worksheets completed, alerts received

## Notable Decisions

1. **WorkManager over Service**: Handles low-memory kills, respects Doze mode
2. **FusedLocationProvider**: Better accuracy + battery than raw GPS
3. **Room for offline queue**: Deterministic retry vs. cloud sync complications
4. **Jetpack Compose**: Modern declarative UI, easier accessibility
5. **Hilt DI**: Type-safe, annotation-driven, integrates with WorkManager
6. **FCM for push**: Free, scalable, works with Play Services
7. **DataStore over SharedPreferences**: Type-safe, coroutine-based
8. **Retrofit over Ktor**: Mature ecosystem, easier plugin architecture

## Debugging

### Enable Verbose Logging
```kotlin
// In AppModule
val loggingInterceptor = HttpLoggingInterceptor().apply {
    level = HttpLoggingInterceptor.Level.BODY
}
```

### WorkManager Debugging
```bash
adb shell dumpsys jobscheduler | grep "floodguard"
adb shell am get-app-links ke.floodguard
```

### Sensor Debugging
```bash
adb shell dumpsys sensorservice | grep PRESSURE
```

### Database Inspection
Use Android Studio Database Inspector:
1. Device Explorer → data/data/ke.floodguard/databases
2. Right-click → Open in New Tab

## Maintenance

- **Update Gradle**: `gradle/wrapper/gradle-wrapper.properties`
- **Kotlin version**: Check Gradle catalogs
- **Play Services**: Monitor deprecation warnings
- **Target SDK**: Update yearly for Play Store requirements
- **Security patches**: Monitor Kotlin + AndroidX releases

## Support

- **Crash reporting**: Firebase Crashlytics
- **Analytics**: Firebase Analytics
- **Remote config**: Feature flags via Firebase Remote Config
- **User feedback**: In-app survey (optional)

---
**Version**: 1.0.0 | **Last Updated**: 2026-04-20 | **Target Devices**: 100,000+ volunteers nationwide
