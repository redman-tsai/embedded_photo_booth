var express = require('express');
var mongo = require("mongodb");
var multer = require('multer');
var path = require('path');
var fs = require('fs');
var bodyparser = require("body-parser");
var mongoose = require('mongoose');
var Schema = mongoose.Schema;
var admzip = require("adm-zip");
var display = require("./display");

//cloud fileserver setup
var app = express();
app.use(express.static('public'));
app.use(bodyparser.json());


//app.listen(9000,'128.230.210.229', function(){
app.listen(8000,'192.168.1.13', function(){
    console.log('Example app listening on port 8000!');
});

//mongodb setup
mongoose.connect("mongodb://localhost:27017/mydb");


var FileSchema = new Schema(
    {
        id: String,
        path: String

    });

mongoose.model('File', FileSchema);

//File schema
var File = mongoose.model('File');


// define disk storage of upload files (control destinations)

var storage = multer.diskStorage({
    destination: function (req, file, uploadfile) {
        uploadfile(null, './public/images')
    },
    filename: function (req, file, cb) {
        cb(null, file.originalname)
    }
});

//function handle upload request

var upload = multer({storage: storage}).any('imagefile');


app.post('/upload', function (req, res) {

    upload(req, res, function (err) {
        if (err) {
            return res.end(" uploading file failed");
        }
        //fs.createReadStream('./upload_files/'+ req.body.filename+".zip").pipe(unzip.Extract({ path: './upload_files' }));
        var zip = new admzip('./public/images/' + req.body.filename + ".zip");
        if (!fs.existsSync('./public/images/'+req.body.filename))
        {
            fs.mkdirSync('./public/images/'+req.body.filename);
            console.log('./public/images/'+req.body.filename+'created');
        }
        zip.extractAllTo('./public/images/'+req.body.filename);
        console.log(req.body.photoid);
        var file = new File({
            id: req.body.photoid,
            path: "/public/images/" + req.body.filename
        });
        file.save(function (err) {
            console.log('save status:', err ? 'failed' : 'success');
        });

        res.end("File is uploaded");
    });

});


//function handle get photos request

app.get('/photos', function (req, res, next) {
    res.sendFile(path.join(__dirname + '/public/getdata.html'));

});

app.get('/getdata', function (req, res) {

        //database query

        File.find({"id": req.query.photoid}, function (err, results) {
            if (err) {
                res.end('Error');
            }

            if (results.length) {

                console.log("\n\n find saved image files, wait for display!");
                var imageDir = results[0].path;

                display.getImages(imageDir, res);

            }
            else {

                res.send("no matched file for input id, try again!");

            }
        })
    }
);




