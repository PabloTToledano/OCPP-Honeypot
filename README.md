# OCPP-Honeypot
TFM Uma 

Necesita vt-py para poder escanear ficheros recibidos por los casos de usos de ficheros/actualizaciones

Podman
podman network create ocpp
podman run --network ocpp --name csms1 csms
podman run --network ocpp --name cp1 charging


Front without logging
podman run --network ocpp -p 5000:5000 --env 'NO_LOG=true' front 

OCPP2.0 Charge Point Simulator adapted from:
 - https://github.com/dallmann-consulting/OCPP.Core/blob/main/Simulators/cp20_mod.html
 - https://github.com/JavaIsJavaScript/OCPP-2.0-CP-Simulator