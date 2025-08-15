#README

##Schema Format:
Name, Duration, Dependency (semicolon-separated if multiple, or empty), Task Type, Parameters (semicolon-separated if multiple).

###Example:
```
trace-dal,20,resolv-dal,traceroute,endpoint=dal.speedtest.clouvider.net;count=10;tool=mtr
```

**Name:** trace-dal
**Duration:** 20 seconds
**Dependency:** resolv-dal
**Task Type:** traceroute
**Parameters:** (separated by semicolons): endpoint=dal.speedtest.clouvider.net;count=10;tool=mtr