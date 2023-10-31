const fs = require('fs');
const NodeID3 = require('node-id3')

let mp3file = process.argv[2];
let id3v2Tags = process.argv[3]; // JSON file

let tags = JSON.parse(fs.readFileSync(id3v2Tags, 'utf8'));

// replace image filenames with image buffers
for (let chapter of tags.chapter) {
    if (chapter.tags.hasOwnProperty('imagefile')) {
        // read image file
        let image = fs.readFileSync(chapter.tags.imagefile);
        delete chapter.tags.imagefile;
        // write as buffer
        chapter.tags.image = {
            mime: 'image/png',
            type: {
                id: 0,
                name: 'other'
            },
            description: '',
            imageBuffer: image
        };
    }
}

if (tags.hasOwnProperty('image')) {
    let image = fs.readFileSync(tags.image.imagefile);
    delete tags.image.imagefile;
    tags.image.imageBuffer = image;
}

NodeID3.write(tags, mp3file);