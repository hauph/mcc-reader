import MCCReader

reader = MCCReader.MCCReader()
reader.read("samples/BigBuckBunny_256x144-24fps.mcc")
print("Languages: ", reader.get_languages())
print("Tracks: ", reader.get_tracks())
print("Captions: ", reader.get_captions())
