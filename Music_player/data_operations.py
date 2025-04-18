from db_connection import get_db_connection
import mysql.connector
from mysql.connector import conversion
from mysql.connector.conversion import MySQLConverter
import io 
import os
from PIL import Image
import matplotlib.pyplot as plt
import json

# Inserting the data into the table
def insert_song(file_path, json_file_path, title, artist_name, album_title, genre_name, album_cover=None, 
                track_number=None, release_year=None, album_type=None, duration=None, total_tracks=None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Start transaction
                conn.start_transaction()
                
                try:
                    # Check if song already exists
                    cursor.execute("SELECT id FROM songs WHERE file_path = %s OR title = %s", 
                                (file_path, title))
                    if cursor.fetchall():  # Consume all results
                        print(f"Song '{title}' already exists in database")
                        return True

                    # Insert or get artist
                    cursor.execute("INSERT IGNORE INTO artists (name) VALUES (%s)", (artist_name,))
                    conn.commit()  # Commit after INSERT
                    cursor.execute("SELECT id FROM artists WHERE name = %s", (artist_name,))
                    artist_result = cursor.fetchall()  # Consume all results
                    artist_id = artist_result[0][0] if artist_result else 1

                    # Insert or get genre
                    cursor.execute("INSERT IGNORE INTO genres (name) VALUES (%s)", (genre_name,))
                    conn.commit()  # Commit after INSERT
                    cursor.execute("SELECT id FROM genres WHERE name = %s", (genre_name,))
                    genre_result = cursor.fetchall()  # Consume all results
                    genre_id = genre_result[0][0] if genre_result else 1

                    # Insert or get album
                    cursor.execute("""
                        INSERT IGNORE INTO albums (title, artist_id, release_year, album_type, total_tracks) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (album_title or "Unknown", artist_id, release_year, album_type, total_tracks))
                    conn.commit()  # Commit after INSERT
                    cursor.execute("SELECT id FROM albums WHERE title = %s AND artist_id = %s", 
                                (album_title or "Unknown", artist_id))
                    album_result = cursor.fetchall()  # Consume all results
                    if not album_result:
                        raise Exception("Failed to get album ID")
                    album_id = album_result[0][0]

                    # Insert music
                    cursor.execute("""
                        INSERT INTO songs (file_path, title, artist_id, album_id, genre_id, 
                                        album_cover, track_number, duration)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (file_path, title, artist_id, album_id, genre_id, 
                          album_cover, track_number, duration))
                    conn.commit()  # Final commit
                    
                    print(f"Successfully inserted song: {title}")
                    return True
                    
                except Exception as e:
                    # Rollback transaction on error
                    conn.rollback()
                    print(f"Transaction failed, rolling back: {e}")
                    return False
                    
    except mysql.connector.Error as e:
        print(f"Error inserting songs data: {e}")
        if e.errno == 1205:  # Lock wait timeout error
            print("Lock timeout occurred, please try again")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def retrieve_song(conditions=None):
    try:
        with get_db_connection() as db_connection:
            with db_connection.cursor() as cursor:
                query = """
                SELECT m.id, m.file_path, m.title, a.name as artist, al.title as album, g.name as genre, m.album_cover, 
                m.track_number, al.release_year, al.album_type, m.duration, al.total_tracks
                FROM songs m
                JOIN artists a ON m.artist_id = a.id
                JOIN albums al ON m.album_id = al.id
                JOIN genres g ON m.genre_id = g.id
                """
                values = []
                
                if conditions:
                    where_clauses = []
                    for k, v in conditions.items():
                        table_prefix = 'm'
                        if k in ['artist', 'name']:
                            table_prefix = 'a'
                        elif k in ['album', 'release_year', 'album_type']:
                            table_prefix = 'al'
                        elif k == 'genre':
                            table_prefix = 'g'
                        where_clauses.append(f"{table_prefix}.{conversion.MySQLConverter().escape(k)} = %s")
                        values.append(v)
                    query += " WHERE " + " AND ".join(where_clauses)

                cursor.execute(query, tuple(values))
                return cursor.fetchall()
    except mysql.connector.Error as e:
        print(f"Error retrieving music data: {e}")
        return []

def display_song(data, show_album_art=False):
    if not data:
        print('No music to display')
        return
    
    headers = ["Title", "Artist", "Album", "Genre", "Album Cover", 
               "Track Number", "Release Year", "Album Type", "Duration"]

    # Print the headers
    print(" | ".join(headers))
    print("-" * (len(headers) * 15)) # Separator lines

    # Print the data rows
    for row in data:
        # Convert LONGBLOB to a placeholder string for display
        row = list(row)
        album_cover_blob = row[6]
        row[6] = "<BLOB>" if album_cover_blob else "None"
        print(" | ".join(str(item) for item in row))
        
        if show_album_art:
            display_album_art(album_cover_blob)
        
def display_album_art(album_cover_blob):
    if album_cover_blob:
        # Convert BLOB to image
        image = Image.open(io.BytesIO(album_cover_blob))
        
        # Display the image
        plt.imshow(image)
        plt.axis('off') # Hide axes
        plt.show()
    else:
        print("No album cover available")
        
def get_song_by_artist(artist):
    return retrieve_song({'artist': artist})

def get_song_by_album(album):
    return retrieve_song({'album': album})

def get_song_by_genre(genre):
    return retrieve_song({'genre': genre}) 

def get_all_song():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM songs")
                songs = cursor.fetchall()
                if not songs:
                    print("No songs found in the database.")
                else:
                    print(f"Found {len(songs)} songs in the database.")
                return songs
    except mysql.connector.Error as e:
        print(f"Error retrieving songs: {e}")
        return []

def get_album_songs(album_title, artist_name=None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT s.id, s.title, s.track_number, a.name as artist, al.title as album, al.total_tracks
                    FROM songs s
                    JOIN artists a ON s.artist_id = a.id
                    JOIN albums al ON s.albums = al.id
                    WHERE al.title = %s
                """ 
                params = [album_title]
                
                if artist_name:
                    query += "AND a.name = %s"
                    params.append(artist_name)
                    
                query += " ORDER BY s.track_number"
                
                cursor.execute(query, tuple(params))
                songs = cursor.fetchall()
                
                if songs:
                    print(f"\nAlbum: {songs[0][4]}")
                    print(f"\nArtist: {songs[0][3]}")
                    print(f"\nTotal Tracks: {songs[0][5]}")
                    print(f"Tracks:")
                    for song in songs:
                        print(f"{song[2]}. {song[1]}")
                    return songs
                
    except mysql.connector.Error as e:
        print(f"Error retrieving album songs: {e}")
        return []
                
def update_song(id, **kwargs):
    updates = {}
    artist_update = None
    album_update = None
    genre_update = None

    for k, v in kwargs.items():
        if k == 'artist':
            artist_update = v
        elif k in ['album', 'release_year', 'album_type', 'total_tracks']:
            if album_update is None:
                album_update = {}
            album_update[k] = v
        elif k == 'genre':
            genre_update = v
        else:
            updates[k] = v

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Start transaction
                conn.start_transaction()
                
                try:
                    # Handle artist update
                    if artist_update:
                        cursor.execute("INSERT IGNORE INTO artists (name) VALUES (%s)", (artist_update,))
                        cursor.execute("SELECT id FROM artists WHERE name = %s", (artist_update,))
                        artist_result = cursor.fetchone()
                        if not artist_result:
                            raise Exception("Failed to get artist ID")
                        updates['artist_id'] = artist_result[0]

                    # Handle genre update
                    if genre_update:
                        cursor.execute("INSERT IGNORE INTO genres (name) VALUES (%s)", (genre_update,))
                        cursor.execute("SELECT id FROM genres WHERE name = %s", (genre_update,))
                        genre_result = cursor.fetchone()
                        if not genre_result:
                            raise Exception("Failed to get genre ID")
                        updates['genre_id'] = genre_result[0]

                    # Handle album update
                    if album_update:
                        if 'album' in album_update:
                            cursor.execute("SELECT artist_id FROM songs WHERE id = %s", (id,))
                            artist_result = cursor.fetchone()
                            if not artist_result:
                                raise Exception("Failed to get artist ID for album")
                            artist_id = artist_result[0]
                            
                            cursor.execute("""
                                INSERT IGNORE INTO albums (title, artist_id, release_year, album_type, total_tracks) 
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                album_update['album'], artist_id, 
                                album_update.get('release_year'), 
                                album_update.get('album_type'),
                                album_update.get('total_tracks')))
                                
                            cursor.execute("""
                                SELECT id FROM albums 
                                WHERE title = %s AND artist_id = %s
                            """, (album_update['album'], artist_id))
                            album_result = cursor.fetchone()
                            if not album_result:
                                raise Exception("Failed to get album ID")
                            updates['album_id'] = album_result[0]
                            
                        elif 'release_year' in album_update or 'album_type' in album_update:
                            cursor.execute("SELECT album_id FROM songs WHERE id = %s", (id,))
                            album_result = cursor.fetchone()
                            if not album_result:
                                raise Exception("Failed to get album ID for update")
                            album_id = album_result[0]
                            
                            converter = MySQLConverter()
                            set_clause = ', '.join([f"{converter.escape(k)} = %s" 
                                                  for k in album_update.keys()])
                            values = tuple(album_update.values()) + (album_id,)
                            cursor.execute(f"UPDATE albums SET {set_clause} WHERE id = %s", values)

                    # Update song details
                    if updates:
                        set_clause = ', '.join([
                            f"{conversion.MySQLConverter().escape(k)} = %s"
                            for k in updates
                        ])
                        values = tuple(updates.values()) + (id,)
                        cursor.execute(f"UPDATE songs SET {set_clause} WHERE id = %s", values)

                    # Commit all changes
                    conn.commit()
                    print(f"Music with ID {id} updated successfully")
                    return True
                    
                except Exception as e:
                    # Rollback on error
                    conn.rollback()
                    print(f"Transaction failed, rolling back: {e}")
                    return False
                    
    except mysql.connector.Error as e:
        print(f"Error updating songs data: {e}")
        if e.errno == 1205:  # Lock wait timeout error
            print("Lock timeout occurred, please try again")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def delete_music(id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                conn.start_transaction()
                
                try:
                    cursor.execute("""
                                   SELECT album_id, artist_id
                                   FROM songs
                                   where id = %s
                                   """, (id,))
                    res = cursor.fetchone()
                    if not res:
                        print(f"Song with ID {id} not found in Database")
                        return
                    
                    album_id, artist_id = res
                    
                    cursor.execute("DELETE FROM songs WHERE id = %s",  (album_id))
                    cursor.execute("SELECT COUNT(*) FROM songs WHERE album_id = %s", (album_id))             
                    
                    if cursor.fetchone()[0] == 0:
                        cursor.execute("DELETE FROM albums WHERE id = %d", (album_id))      
                        
                    cursor.execute("SELECT COUNT(*) FROM songs WHERE artist_id = %s")
                    if cursor.fetchone()[0] == 0:
                        cursor.execute("DELETE FROM artists WHERE id = %s", (artist_id))
                        
                    conn.commit()
                    print(f"Music with ID {id} and related records deleted successfully")
                except Exception as e:
                    conn.rollback()
                    print(f"Error during deletion song with ID {id}")
                    raise
    except mysql.connector.Error as e:
        print(f"Error deleting song with ID {id}")
        
                            
def reading_parsed_json(json_file_path):
    try:
        # First try to open and read the JSON file
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return extracting_json_data(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error parsing JSON file: {e}")
        # Return default metadata if file doesn't exist or is invalid
        return {
            'title': os.path.splitext(os.path.basename(json_file_path))[0],
            'artist': 'Unknown',
            'album': 'Unknown',
            'genre': 'Unknown',
            'track_number': None,
            'duration': None,
            'release_year': None,
            'album_type': None
        }

def extracting_json_data(f):
    data = json.load(f)

    # Extract the relevant info
    title = data.get('title', '')
    artist = data.get('artist', '')
    album = data.get('album', '')
    genre = data.get('genre', '')
    track_number = data.get('track_number')
    total_tracks = data.get('total_tracks')
    duration = data.get('duration')

    release_year = data.get('release_date', '').split('-')[0] if data.get('release_date') else None
    album_type = data.get('album_type', '')

    return {
        'title': title,
        'artist': artist,
        'album': album,
        'genre': genre,
        'track_number': track_number,
        'total_tracks': total_tracks,
        'duration': duration,
        'release_year': release_year,
        'album_type': album_type
    }
           