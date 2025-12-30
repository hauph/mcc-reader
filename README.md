docker build -t mcc-reader . 


docker run -v $(pwd)/samples:/app/samples mcc-reader \
    python test.py


docker run -v $(pwd)/samples:/app/samples mcc-reader \
    python decoder.py samples/AXMT3111100H.mcc -o samples/output
