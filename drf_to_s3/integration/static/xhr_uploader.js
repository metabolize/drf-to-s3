var S3Uploader = function (base_url) {
    this.base_url = base_url;
};

S3Uploader.prototype.set_upload_content = function (filename, content_type, content) {
    this.filename = filename;
    this.upload_content_type = content_type;
    this.upload_content = content;
};

S3Uploader.prototype._send_request = function (method, url, content, content_type) {
    var deferred = $.Deferred();

    var xhr = new XMLHttpRequest();

    xhr.open(method, url, true);

    if (content_type) {
        xhr.setRequestHeader('Content-Type', content_type);
    }
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));

    xhr.onload = function (event) {
        var response = event.target.response;
        if (event.target.getResponseHeader('Content-Type') == 'application/json') {
            response = JSON.parse(response);
        }
        if (event.target.status >= 200 && event.target.status < 400) {
            deferred.resolve(response);
        } else {
            deferred.reject(response);            
        }
    };

    xhr.onerror = function (event) {
        deferred.reject(event);
    };

    xhr.onprogress = function (event) {
        deferred.notify(event);
    };

    xhr.send(content);

    return deferred.promise();
};

S3Uploader.prototype.get_upload_uri = function () {
    var uploader = this;

    var deferred = $.Deferred();

    var url = uploader.base_url + 'api/s3/upload_uri';

    uploader._send_request('POST', url, undefined)
    .done(function (response) {

        uploader.upload_uri = response.upload_uri;
        uploader.dst_key = response.key;

        deferred.resolve();

    })
    .fail(function (event) {

        deferred.reject({
            message: "Couldn't get signed upload URL",
            event: event,
        });  

    });

    return deferred.promise();
};

S3Uploader.prototype.upload_to_s3 = function () {
    var uploader = this;

    var deferred = $.Deferred();

    if (! uploader.upload_uri) {
        throw new Error("upload_uri is not set");
    }

    uploader._send_request('PUT', uploader.upload_uri, uploader.upload_content)
    .done(function (response) {

        deferred.resolve();

    })
    .fail(function (error) {

        deferred.reject({
            message: "Couldn't upload to S3",
            event: event,
        });  

    });

    return deferred.promise();
};

S3Uploader.prototype.post_upload_callback = function () {
    var uploader = this;

    var deferred = $.Deferred();

    if (! uploader.dst_key) {
        throw new Error("dst_key is not set");
    }

    var url = uploader.base_url + 'api/s3/file_uploaded';

    var payload = {
        key: uploader.dst_key,
        filename: uploader.filename,
    };

    uploader._send_request('POST', url, JSON.stringify(payload), 'application/json')
    .done(function (response) {

        deferred.resolve(response);

    })
    .fail(function (error) {

        deferred.reject({
            message: "Uploaded callback failed",
            event: event,
        });

    });

    return deferred.promise();
};

S3Uploader.prototype.start = function () {
    var uploader = this;

    var deferred = $.Deferred();

    console.log("Starting upload");

    uploader.get_upload_uri()
    .then(function () {
        console.log("Got signed upload URI");

        return uploader.upload_to_s3();
    })
    .then(function () {
        console.log("Successfully uploaded to S3");

        return uploader.post_upload_callback();
    })
    .then(function () {
        console.log("Successfully hit post-upload callback");
        console.log("Upload complete");
        deferred.resolve();
    })
    .fail(function (error) {
        console.log(error);
        deferred.reject(error);
    });

    return deferred.promise();
};

