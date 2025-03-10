## Data Cleaning

Guideline and instructions on how the data was cleaned.

### Clean Data



### Clean Route

Run with `python3 clean_route.py ../Data/2.\ Routes/raw-CstU.geojson`

1. Stockholm (Cst) - Uppsala (U) (Arlanda)

    * Initial point (Way 137012054): 

        ```
        Longitude: 18.0558889
        Latitude: 59.331247
        ```

    * New point (Way 137006830):

        ```
        Longitude: 18.0531927
        Latitude: 59.3335289
        ```

    * Choice 1 (Way 211795421)

    * Choice 1 (Way 206137367)

    * Choice 0 (Way 137142001)

    * Abort (save to `../Data/2. Routes/route-CstU-arlanda.json`)

2. Stockholm (Cst) - Uppsala (U) (Straight)

    * Initial point (Way 137012054): 

        ```
        Longitude: 18.0558889
        Latitude: 59.331247
        ```

    * New point (Way 137006830):

        ```
        Longitude: 18.0531927
        Latitude: 59.3335289
        ```

    * Choice 0 (Way 136785303)

    * Choice 1 (Way 206137367)

    * Choice 0 (Way 137142001)

    * Abort (save to `../Data/2. Routes/route-CstU-straight.json`)



    