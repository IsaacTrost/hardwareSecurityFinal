# Project 3 - FitHealth Database
This top-level directory contains the deployment and startup scripts for the TDX-secured and unsecured versions of the FitHealth Database.

## Report location:
The report for this project is in FitHealthReport.pdf, which is in the top-level directory of this repository.

## Project layout:
data: This directory contains data from the tests run on this project.

docker-sqlcipher-service-insecure: This directory contains the Dockerfile and scripts to build and run the unsecured version of the FitHealth database.

docker-sqlcipher-service-secure: This directory contains the Dockerfile and scripts to build and run the TDX-secured version of the FitHealth database.

testing: This directory contains the test scripts and data to test the project.


### Quote Verification Setup
Quote verification and attestation are handled by two services: QVS (QuoteVerificationService) and SSS (Simple Signing Service).
Each of these services must be running in their own Docker containers at the time of remote attestation. To build and deploy these 
containers, follow documentation found on their respective repositories: [QVS](https://github.com/intel/SGX-TDX-DCAP-QuoteVerificationService), [QVL](https://github.com/intel/SGX-TDX-DCAP-QuoteVerificationLibrary). Once running, a quote can be verified by making the 
appropriate POST request to the verificatoin endpoint.

**NOTE:** Each repository must be cloned at the same level and with the directory names QVS and QVL for proper path resolution. Then,
running ./build.sh and ./runAll.sh from the QVS repo should build the images as needed.

Clone these two repos at the same level, and name them QVS and QVL respectively (important for path resolution). 
