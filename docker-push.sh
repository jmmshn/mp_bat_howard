#!/bin/bash
date_tag=$(date +"%Y-%m-%d")
version=$1
full_tag=$(echo "${date_tag}${version}")
echo $full_tag
sed -i'.original' "s/url_base_pathname.*/url_base_pathname=\'\/vw\/\',/g" app.py
sed -i'.original' "s/assets_url_path.*/assets_url_path=\'\/vw\'/g" app.py
sed -i'.original' "s/^DEFAULT_CATION.*/DEFAULT_CATION=\'Mg\'/g" app.py
sed -i'.original' "s/^DEFAULT_STRUCT.*/DEFAULT_STRUCT=\'43457_Mg\'/g" app.py
cp ./secrets/db_info_vw.json ./secrets/db_info.json
docker build -t registry.spin.nersc.gov/perssongroup/vw:$full_tag .
docker push registry.spin.nersc.gov/perssongroup/vw:$full_tag

sed -i'.original' "s/url_base_pathname.*/url_base_pathname=\'\/basf\/\',/g" app.py
sed -i'.original' "s/assets_url_path.*/assets_url_path=\'\/basf\'/g" app.py
sed -i'.original' "s/^DEFAULT_CATION.*/DEFAULT_CATION=\'Li\'/g" app.py
sed -i'.original' "s/^DEFAULT_STRUCT.*/DEFAULT_STRUCT=\'65041_Li\'/g" app.py
cp ./secrets/db_info_basf.json ./secrets/db_info.json
docker build -t registry.spin.nersc.gov/perssongroup/basf:$full_tag .
docker push registry.spin.nersc.gov/perssongroup/basf:$full_tag
