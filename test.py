from MCCReader import MCCReader

reader = MCCReader()
reader.read("samples/AXMT3111100H.mcc", output_dir="samples/output")
# print("Debug metadata: ", reader.get_debug_metadata())
# print("Original result: ", reader.get_original_result())
# print("Tracks: ", reader.get_tracks())
# print("Tracks: ", reader.get_tracks("cea608"))

# print("Languages: ", reader.get_languages())
# print("Languages: ", reader.get_languages("cea608"))

# print("Formats: ", reader.get_formats())

# print("fps: ", reader.get_fps())
# print("Drop Frame: ", reader.get_drop_frame())

# print("Languages to tracks: ", reader._languages_to_tracks)
# print("Tracks to languages: ", reader._tracks_to_languages)

# print("Captions - Default: ", reader.get_captions())
# print("Captions - With format: ", reader.get_captions(format="cea608"))
# print("Captions - Wrong format: ", reader.get_captions(format="ebustl"))
# print(
#     "Captions - Format and Language: ",
#     reader.get_captions(format="cea608", language="es"),
# )
# print("Captions - Language without format: ", reader.get_captions(language="en"))
# print(
#     "Captions - Wrong Language: ",
#     reader.get_captions(format="cea708", language="vn"),
# )
