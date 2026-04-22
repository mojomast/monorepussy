# VHS tape file for terrariumussy demo recording
# Usage: vhs demo/record.tape
# Output: demo/assets/demo.gif

Output demo/assets/demo.gif

Set FontSize 16
Set Width 960
Set Height 600
Set Padding 20
Set Theme "Nord"

Type "terrarium health ."
Sleep 500ms
Enter
Sleep 2s

Type "terrarium dashboard"
Sleep 500ms
Enter
Sleep 3s

Type "q"
Sleep 500ms

Type "terrarium export --format json"
Sleep 500ms
Enter
Sleep 2s

Type "cat demo/fixtures/demo_health.json | python3 -m json.tool | head -30"
Sleep 500ms
Enter
Sleep 2s
