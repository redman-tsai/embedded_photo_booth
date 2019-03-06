var fs = require("fs");
var path = require('path');


module.exports = {

    //display image to user

    getImages: function (imageDir, res) {

        var images = [];

        var imagepath = "." + imageDir;
        var folder = imageDir.substr(8);

        //get each image in the folder

        fs.readdir(imagepath, function (err, files) {
                var imageLists = "<div style='color:royalblue; text-align:center; font-size: 75px;  font-style: oblique; font-weight: bold ; margin-top: 0px; margin-bottom: 100px' >Photos Gallery</div>\n<ul>\n";
                for (var i = 0; i < files.length; i++) {
                    if (path.extname(files[i]) === ".png") {
                        images.push(files[i]);
                        imageLists += "<img src='" + folder + "/" + files[i] + "'" + ' height= "300" width="300" > \n';
                        imageLists += ' <input type="checkbox" name = "image"  value="' + folder + "/" + files[i] + '"/>\n';
                    }
                }
                imageLists += '</ul>';


                res.writeHead(200, 'Content-type:text/html');

                fs.readFile("./public/download.html", "utf8", function (err, data) {

                    imageLists += data;

                    res.write(imageLists);
                    res.end();

                });

            console.log(" \n photos display to client for select!!");

            }
        )

    }
};

