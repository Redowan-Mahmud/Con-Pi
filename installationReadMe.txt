# COPY the SoftwarePackage folder to PiDesktop 
# Make sure internet is okay
1. RUN sudo raspi-config
2. GOTO Interfacing Options
3. SELECT Camera
4. ENABLE Yes
5. SELECT finish
6. REBOOT
7. CONNECT Motion sensor: power pin T2, gnd pin B5, input pin T18
8. CONNECT Repeller: power pin T1, gnd pin T3, output pin T19 
9. RUN sh install_script.sh
10. REBOOT

# Delete the SoftwarePackage folder to PiDesktop 
