from sys import argv

def url_list_generator():
    with open('config/banners.txt', 'r') as f:
        first_line = True
        out_string = "\n"
        for line in f:
            if first_line == True:
                if line == '':
                    return
                out_string += "            \""+line.strip()+"\"\n"
                first_line = False
            else:
                out_string += "           , \""+line.strip()+"\"\n"
    return out_string

def css_importer():
    with open('config/styles.css', 'r') as f:
        out_string = '\n'
        for line in f:
            out_string += "    "+str(line.rstrip())+"\n"
    return out_string

def generate_supertable():
    pass

def generate_sidetable():
    pass

def generate_killtable():
    pass


current_month_year = "August, 2016"
killmail_table = """
<table class="super-table">
<tbody>
<tr>
<td>
<table class="kb-table">
    <tbody>
        <tr>
            <td>ShipType</td>
            <td>Pilot</td>
            <td>Final Blow</td>
            <td>Location</td>
        </tr>
        <tr class="kb-table-row-even-kill">
            <td>Spaceship</td>
            <td>Enemy Character Name</td>
            <td>Friendly Character Name</td>
            <td>TVN-FM</td>
        </tr>
        <tr class="kb-table-row-odd-loss">
            <td>Spaceship</td>
            <td>Friendly Character Name</td>
            <td>Enemy Character Name</td>
            <td>TVN-FM</td>
        </tr>
        <tr class="kb-table-row-even-kill">
            <td>Spaceship</td>
            <td>Enemy Character Name</td>
            <td>Friendly Character Name</td>
            <td>TVN-FM</td>
        </tr>
        <tr class="kb-table-row-odd-kill">
            <td>Spaceship</td>
            <td>Enemy Character Name</td>
            <td>Friendly Character Name</td>
            <td>TVN-FM</td>
        </tr>
        <tr class="kb-table-row-even-loss">
            <td>Spaceship</td>
            <td>Friendly Character Name</td>
            <td>Enemy Character Name</td>
            <td>TVN-FM</td>
        </tr>
        <tr class="kb-table-row-odd-loss">
            <td>Spaceship</td>
            <td>Friendly Character Name</td>
            <td>Enemy Character Name</td>
            <td>TVN-FM</td>
        </tr>
    </tbody>
</table>
</td>
<td>
<table class="stats-table">
    <tbody>
        <tr class="stats-header"><td>Active PVP</td></tr>
        <tr><td>Characters</td><td>3</td></tr>
        <tr><td>Ships</td><td>4</td></tr>
        <tr><td>Total Kills</td><td>30</td></tr>
    </tbody>
</table>
"""

    # <script src=https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js></script>
    # <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
    # <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css" integrity="sha384-rHyoN1iRsVXV4nD0JutlnGaslCJuC7uwjduW9SVrLvRYooPp2bWYgmgJQIXwl/Sp" crossorigin="anonymous">
    # <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>

output_html = """
<html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Polyhedra Killboard</title>
    <script type="text/javascript">
        var imageUrls = [""" + url_list_generator() + """        ];

      function getImageHtmlCode() {
        var dataIndex = Math.floor(Math.random() * imageUrls.length);
        var img = '<center><img src=\"';
        img += imageUrls[dataIndex];
        img += '\" alt=\"Polyhedra Killboard\"/></a></center>';
        return img;
      }
    </script>
    <style>""" + css_importer() + """    </style>
    </head>

<body>
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

