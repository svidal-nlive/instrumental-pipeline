#!/bin/sh

# Directories to adjust ownership
DIRS="/deemix_audio_files /pdl_audio_files /audio_files"

for d in $DIRS; do
    if [ -d "$d" ]; then
        chown -R ${PUID}:${PGID} "$d"
    else
        echo "Directory $d does not exist, skipping chown" >> /tmp/file_watcher.log
    fi
done

# Define Source Directories (Monitored Paths)
WATCH_DIRS="/deemix_audio_files /pdl_audio_files"

# Define Destination Directory
DEST_DIR="/audio_files"

# Define Backend API URL
BACKEND_URL="http://backend:8000/upload/"

# Log file
LOG_FILE="/tmp/file_watcher.log"
echo "----------------------------------------------------------------------" >> ${LOG_FILE}
echo "File Watcher Started: Monitoring ${WATCH_DIRS}" >> ${LOG_FILE}
echo "----------------------------------------------------------------------" >> ${LOG_FILE}

# Function to check if a file is fully written (stable file size)
is_file_stable() {
    local file="$1"
    local prev_size=0
    local current_size=0

    while true; do
        current_size=$(stat -c%s "$file" 2>/dev/null || echo 0)
        if [ "$current_size" -eq 0 ]; then
            echo "File $file is empty, waiting..." >> ${LOG_FILE}
            sleep 5
            continue
        fi
        if [ "$current_size" -eq "$prev_size" ] && [ "$current_size" -gt 0 ]; then
            sleep 5
            new_size=$(stat -c%s "$file" 2>/dev/null || echo 0)
            if [ "$new_size" -eq "$current_size" ]; then
                return 0
            else
                prev_size=0
                continue
            fi
        fi
        prev_size=$current_size
        sleep 2
    done
}

# Function to clean up a directory if it contains no MP3 files
cleanup_dir_if_no_mp3() {
    local dir="$1"
    if [ -d "$dir" ]; then
        mp3_count=$(find "$dir" -maxdepth 1 -type f -iname "*.mp3" | wc -l)
        if [ "$mp3_count" -eq 0 ]; then
            rm -r "$dir"
            echo "Removed directory: $dir" >> ${LOG_FILE}
        fi
    fi
}

# Function to process a newly detected file
process_file() {
    FILE="$1"
    if [ -f "$FILE" ] && echo "$FILE" | grep -qiE "\.mp3$"; then
        echo "Detected new file: $FILE" >> ${LOG_FILE}
        echo "Waiting for $FILE to be fully written..." >> ${LOG_FILE}
        if is_file_stable "$FILE"; then
            echo "File is stable: $FILE" >> ${LOG_FILE}
        else
            echo "File did not stabilize: $FILE" >> ${LOG_FILE}
            return
        fi

        FILENAME=$(basename "$FILE")
        # Convert filename to snake_case using Python
        SNAKE_CASE_FILENAME=$(python3 common.py "$FILENAME")
        DEST_PATH="$DEST_DIR/$SNAKE_CASE_FILENAME"

        if [ -f "$DEST_PATH" ]; then
            echo "Duplicate file detected: $DEST_PATH exists. Removing $FILE." >> ${LOG_FILE}
            rm "$FILE"
            return
        fi

        mv "$FILE" "$DEST_PATH"
        echo "Moved: $FILE -> $DEST_PATH" >> ${LOG_FILE}

        # Clean up the source directory if no MP3 files remain
        cleanup_dir_if_no_mp3 "$(dirname "$FILE")"

        # Notify backend
        curl -X POST "http://backend:8000/status/track" \
             -H "Content-Type: application/json" \
             -d "{\"file_name\": \"$SNAKE_CASE_FILENAME\"}" >> ${LOG_FILE} 2>&1

        # Trigger processing via backend API with retries
        for i in 1 2 3; do
            RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND_URL" \
              -H "accept: application/json" \
              -H "Content-Type: multipart/form-data" \
              -F "file=@$DEST_PATH" \
              -F "model=5stems")
            if [ "$RESPONSE" -eq 200 ]; then
                echo "API request successful for: $SNAKE_CASE_FILENAME" >> ${LOG_FILE}
                return
            else
                echo "Attempt $i: API request failed (HTTP $RESPONSE), retrying..." >> ${LOG_FILE}
                sleep 5
            fi
        done

        echo "Failed to send API request after multiple attempts for $SNAKE_CASE_FILENAME." >> ${LOG_FILE}
    fi
}

# Start monitoring directories for new files
inotifywait -m -r -e create --format "%w%f" $WATCH_DIRS | while read -r FILE
do
    process_file "$FILE" &
done
