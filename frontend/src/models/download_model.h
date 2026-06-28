#ifndef DOWNLOAD_MODEL_H
#define DOWNLOAD_MODEL_H

#include <QString>
#include <QJsonObject>

struct DownloadModel {
    QString id;
    QString url;
    QString filename;
    QString status = "pending";
    qint64 size = 0;
    qint64 downloaded = 0;
    double speed = 0.0;
    double eta = 0.0;

    static DownloadModel fromJson(const QJsonObject& obj) {
        DownloadModel model;
        model.id = obj.value("id").toString();
        model.url = obj.value("url").toString();
        model.filename = obj.value("filename").toString();
        model.status = obj.value("status").toString();
        
        // Use toDouble() and cast for safe parsing of large numbers (QJsonValue doesn't have toInt64 in older Qt, toDouble handles JS numbers)
        model.size = static_cast<qint64>(obj.value("size").toDouble());
        model.downloaded = static_cast<qint64>(obj.value("downloaded").toDouble());
        model.speed = obj.value("speed").toDouble();
        model.eta = obj.value("eta").toDouble();
        
        return model;
    }
};

#endif // DOWNLOAD_MODEL_H
