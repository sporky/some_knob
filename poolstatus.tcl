proc script::run {} {
    # jrahm inspired
    # https://community.f5.com/t5/codeshare/collect-all-partition-pool-member-stats-with-tmsh/ta-p/315506
    #
    # where to store the data - /shared/images
    set fp [open "/shared/images/poolstatus.json" w+]

    tmsh::cd /
    set device ""
    # hand creating json.. *sigh*
    puts $fp "\["
    # iterate through pools
    foreach pool [tmsh::get_config /ltm pool recursive] {
        set pl [tmsh::get_name $pool]
        foreach obj [tmsh::get_status /ltm pool $pl detail] {
            # if additional fields are desired, do a show ltm pool whatever detail field-fmt
            # and go nuts with it
            set pool_avail [tmsh::get_field_value $obj status.availability-state]
            foreach member [tmsh::get_field_value $obj members] {
                set mbr [tmsh::get_name $member]
                set monitor_status [tmsh::get_field_value $member monitor-status]
                set session_status [tmsh::get_field_value $member session-status]
                set member_avail [tmsh::get_field_value $member status.availability-state]
                puts $fp "\{ \"device\": \"$device\", \"pool\": \"$pl\", \"pool_avail\": \"$pool_avail\", \"member\": \"$mbr\", \"monitor_status\": \"$monitor_status\", \"member_avail\": \"$member_avail\"\, \"session_status\": \"$session_status\" \} , "
            }
        }
    }
    puts $fp "\{ \"device\": \"$device\", \"pool\": \"trash\", \"pool_avail\": \"trash\", \"member\": \"trash\", \"monitor_status\": \"trash\", \"member_avail\": \"trash\", \"session_status\": \"trash\" \} "
    puts $fp "\]"
    close $fp
}
