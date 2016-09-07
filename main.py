from sys import argv

print "\nOpening the index.html for writing..."
with open('out/index.html', 'w') as target:
    target.truncate()

    target.write("<h1>Polyhedra</h1>")
    target.write("\n")
    target.write("<p>a personal Eve tool</p>")
    target.write("\n")
    target.write("<p><small>Hosted on GitHub Pages, Travis-CI was here</p>")
    target.write("\n")

    print "Done writing to index.html!\n"

