import MCCReader

reader = MCCReader.MCCReader()
reader.read("samples/BigBuckBunny_256x144-24fps.mcc")
print("Languages: ", reader.get_languages())
print("Tracks: ", reader.get_tracks())
print("Formats: ", reader.get_formats())
print("Languages to tracks: ", reader._languages_to_tracks)
print("Tracks to languages: ", reader._tracks_to_languages)
print("Captions: ", reader.get_captions())
