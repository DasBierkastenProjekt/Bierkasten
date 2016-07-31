#! /usr/bin/python

# server.py (c) 2016 by Karsten Lehmann

###############################################################################
#                                                                             #
#    This file is a part of Das Bierkastenprojekt                             #
#                                                                             #
#    Das Bierkastenprojekt is free software: you can redistribute it and/or   #
#    modify it under the terms of the GNU General Public License as published #
#    by the Free Software Foundation, either version 3 of the License, or any #
#    later version.                                      		      #
#                                                                             #
#    This program is distributed in the hope that it will be useful,          #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
#    GNU General Public License for more details.                             #
#                                                                             #
#    You should have received a copy of the GNU General Public License        #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.    #
###############################################################################

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import bier

bk = bier.get_bierkasten()

PORT = 6000

class BierHTTPRequestHandler(BaseHTTPRequestHandler):

    def set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text-html")
        self.end_headers()

    def do_GET(self):
        if "get_temperature" in self.path and bk.has_temperature():
            self.set_headers()
            self.wfile.write(bk.get_temperature())

        elif "get_bier_data" in self.path and bk.has_bier_data():
            self.set_headers()
            self.wfile.write(bk.get_bier_data().data)

        elif "daemon_running" in self.path:
            self.set_headers()
            self.wfile.write("running")

        else:
            self.send_error(404)

def webserver():
      server_address = ('', PORT)
      httpd = HTTPServer(server_address, BierHTTPRequestHandler)
      httpd.serve_forever()

if __name__ == "__main__":
    webserver()
