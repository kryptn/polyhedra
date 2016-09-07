from sys import argv

current_month_year = "August, 2016"
killmail_table = """
<font color="#cccccc">
<table style="margin-left: auto; margin-right: auto; text-align: left; color: #cccccc" cellspacing="1" >
    <tbody>
        <tr>
            <td>ShipType</td>
            <td>Pilot</td>
            <td>Final Blow</td>
            <td>Location</td>
        </tr>
        <tr>
            <td>Spaceship</td>
            <td>Character Name</td>
            <td>Character Name</td>
            <td>TVN-FM</td>
        </tr>
    </tbody>
</table>
</font>
"""

url_list = """
            "http://i.imgur.com/7xoyXNi.png"
           , "http://i.imgur.com/9snwgBB.png"
           , "http://i.imgur.com/JEHCad1.png"
           , "http://i.imgur.com/ZuywHbC.png"
           , "http://i.imgur.com/BkqEvW4.gif"
           , "http://i.imgur.com/I6F2msY.png"
"""
output_html = """
<html>
    <head/>
    <title>Polyhedra Killboard</title>
    <script type="text/javascript">
        var imageUrls = [""" + url_list + """];

      function getImageHtmlCode() {
        var dataIndex = Math.floor(Math.random() * imageUrls.length);
        var img = '<center><img src=\"';        
        img += imageUrls[dataIndex];
        img += '\" alt=\"Polyhedra Killboard\"/></a></center>';
        return img;
      }
    </script>
    </head>
    
<body bgcolor="black">
<script type="text/javascript">
  document.write(getImageHtmlCode());
</script>
<font color="#2a9fd6">
<center><h1>Polyhedra</h1></center>
<p>a personal Eve tool</p></font>
<p><font color="#cccccc">"""+current_month_year+"""</font>
"""+killmail_table+"""
</body>
</html>
"""

print "\nOpening the index.html for writing..."
with open('out/index.html', 'w') as target:
    target.truncate()

    target.write(output_html)

    print "Done writing to index.html!\n"

