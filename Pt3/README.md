# Project 3 - FitHealth Database
This top-level directory contains the deployment and startup scripts for the TDX-secured and unsecured versions of the FitHealth Database.

### Quote Verification Setup
Quote verification and attestation are handled by two services: QVS (QuoteVerificationService) and SSS (Simple Signing Service).
Each of these services must be running in their own Docker containers at the time of remote attestation. To build and deploy these 
containers, follow documentation found on their respective repositories: [QVS](https://github.com/intel/SGX-TDX-DCAP-QuoteVerificationService), [QVL](https://github.com/intel/SGX-TDX-DCAP-QuoteVerificationLibrary). Once running, a quote can be verified by making the 
appropriate POST request to the verificatoin endpoint.

**NOTE:** Each repository must be cloned at the same level and with the directory names QVS and QVL for proper path resolution. Then,
running ./build.sh and ./runAll.sh from the QVS repo should build the images as needed.

Clone these two repos at the same level, and name them QVS and QVL respectively (important for path resolution). 
