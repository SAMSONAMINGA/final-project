/**
 * Room Database DAO
 * Data access layer for barometer readings persistence
 */

package ke.floodguard.data.local

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface ReadingDao {
    @Insert
    suspend fun insert(reading: ReadingEntity): Long

    @Query("SELECT * FROM barometer_readings WHERE uploaded = 0 ORDER BY createdAtLocal ASC")
    suspend fun getPendingReadings(): List<ReadingEntity>

    @Query("SELECT COUNT(*) FROM barometer_readings WHERE uploaded = 0")
    fun getPendingReadingsCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM barometer_readings WHERE DATE(createdAtLocal / 1000, 'unixepoch') = DATE('now')")
    suspend fun getReadingsCountToday(): Int

    @Update
    suspend fun update(reading: ReadingEntity)

    @Delete
    suspend fun delete(reading: ReadingEntity)

    @Query("DELETE FROM barometer_readings WHERE uploaded = 1")
    suspend fun deleteUploadedReadings()

    @Query("SELECT * FROM barometer_readings LIMIT 1")
    suspend fun getLastReading(): ReadingEntity?
}
