#!/usr/bin/env python3

# tomsom
# Derived from Sara Edwards' SANS FOR518

# Truffleshuffle is a simple script that parses the Mac OS
# ChunkStoreDatabase and ChunkStorage to carve versioned files.

import os
import sqlite3
from argparse import ArgumentParser
import struct
import sys

parser = ArgumentParser()
parser.add_argument("-c", "--csfile", help="ChunkStorage File")
parser.add_argument("-d", "--csdb",   help="ChunkStoreDatabase SQLite File")
parser.add_argument("-o", "--outdir", help="Output folder", default="Output")
options = parser.parse_args()

try:
   if not os.path.exists(options.outdir):
      os.makedirs(options.outdir)
except OSError as err:
   print(f"OS error - {str(err)}")
   sys.exit(1)

# open ChunkStoreDatabase and ChunkStorage file
with sqlite3.connect(options.csdb) as db:
    with open(options.csfile, 'rb') as cs:
        try:
            # Extracting chunk lists
            for row in db.execute('SELECT clt_rowid,clt_inode,clt_count,clt_chunkRowIDs FROM CSStorageChunkListTable'):
                clt_rowid, clt_inode, clt_count, clt_chunkRowIDs = row
                filename = f"{options.outdir}/{clt_inode}-{clt_rowid}"
                number_of_chunks = len(clt_chunkRowIDs)//8

                # Sanity check
                if number_of_chunks != clt_count:
                    print("WARNING: number of chunks inconsistent!")

                # Open output file            
                with open(filename, 'wb') as output:
                
                    for i in range(len(clt_chunkRowIDs)//8):
                        (chunk_id,) = struct.unpack("<Q",clt_chunkRowIDs[i*8:i*8+8])

                        # Extracting chunks
                        for [offset, dataLen, cid] in db.execute("SELECT offset,dataLen,cid from CSChunkTable where ct_rowid = ?", (chunk_id,)):
                            filenameraw = f"{options.outdir}/{clt_inode}-{clt_rowid}-{chunk_id}-raw" 
                            print(filenameraw)

                            # Append the actual chunk data to the output file
                            cs.seek(offset + 25)
                            chunkData = cs.read(dataLen - 25)
                            output.write(chunkData)

                            # Write the chunk data with header to the RAW output file
                            cs.seek(offset)
                            chunkDataRaw = cs.read(dataLen)

                            # Sanity checks
                            if struct.unpack(">l", chunkDataRaw[0:4])[0] != dataLen:
                                print("WARNING: Chunk size inconsistent!")

                            if chunkDataRaw[4:25].hex() != cid.hex():
                                print("WARNING: Chunk ID inconsistent!")

                            with open(filenameraw,'wb') as outputraw:
                                outputraw.write(chunkDataRaw)


        except sqlite3.Error as err:
            print(f"SQLite error - {str(err)}")
            sys.exit(1)


