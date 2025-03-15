#!/bin/sh
echo "Adjusting permissions on Docker volumes..."
chown -R ${PUID}:${PGID} /audio_files /deemix_audio_files /pdl_audio_files
echo "Permissions adjusted."
# Optionally, you can switch to the non-root user for running subsequent commands.
# If desired, uncomment the next line (make sure 'su-exec' or similar is installed).
# exec su-exec ${PUID}:${PGID} "$@"
exec "$@"
