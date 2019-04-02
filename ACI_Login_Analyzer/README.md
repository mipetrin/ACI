Simple application that connects to the APIC and displays the AAA logs

> It will then produce a simple report for you, that includes all the following; Timestamp, ID, User, Action, Description, Result

It can be executed via the following:
* -u is your APIC cluster

* -l is your login username

*  --start START         Start Date/Time for the search until either --end
                        date/time or current date/time. Full Format:
                        2018-02-23T08:14:25
*  --end END             End Date/Time for the search until either --start
                        date/time or the beginning of the records. Full
                        Format: 2018-02-23T08:14:25
*  --user USER           Find records for a specific user. Default is all. Use
                        "UNKNOWN" to see unknown attempts. Can also look for
                        "root"
*  --action {login,logout,refresh}
                        Find records for this specific action. Default is all
*  --result {Success,Failure}
                        Specify an result to filter on. Default is all
*  --sort {asc,desc}     Specify the sort order. Default is Descending. i.e.
                        Newest logs at the top


```YAML
# python aci_login_analyzer.py -u https://10.66.80.242 -l mipetrin --help
# python aci_login_analyzer.py -u https://10.66.80.242 -l mipetrin --action login --user root
# python aci_login_analyzer.py -u https://10.66.80.242 -l mipetrin --action login --user root --start 2018-02-28T00:00 --end 2018-03-08T23:59
# python aci_login_analyzer.py -u https://10.66.80.242 -l mipetrin --result Failure --start 2018-02-28T00:00 --end 2018-03-08T23:59 --user UNKNOWN
```


Created by Michael Petrinovic 2018


WARNING:

These scripts are meant for educational/proof of concept purposes only - as demonstrated at Cisco Live and/or my other presentations. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and I am not responsible for any damage or data loss incurred as a result of their use