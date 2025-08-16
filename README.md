# README

## Prerequisites:
- [iperf3](https://iperf.fr/iperf-download.php)
- [mtr](https://github.com/traviscross/mtr) 

## Schema Format:
Name, Duration, Dependency (semicolon-separated if multiple, or empty), Task Type, Parameters (semicolon-separated if multiple).

### Examples:
```
trace-dal,20,resolv-dal,traceroute,endpoint=dal.speedtest.clouvider.net;count=10;tool=mtr
```

**Name:** trace-dal  
**Duration:** 20 seconds  
**Dependency:** resolv-dal  
**Task Type:** traceroute  
**Parameters:** (separated by semicolons): endpoint=dal.speedtest.clouvider.net;count=10;tool=mtr  

Feature-full example "dallas.txt" is provided.  

### Useful Links
- [R0GGER's Public iperf3 server list](https://github.com/R0GGER/public-iperf3-servers)
