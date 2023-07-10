import os

x=1
for photo in os.listdir('photos'):
    os.rename(os.path.join('photos', photo), f"photos/{str(x)}.jpg")
    x+=1
