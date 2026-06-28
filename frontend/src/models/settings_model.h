#ifndef SETTINGS_MODEL_H
#define SETTINGS_MODEL_H

#include <QString>
#include <QJsonObject>

struct SettingsModel {
    QString download_folder;
    int max_concurrent = 3;
    bool auto_extract = false;
    bool delete_after = false;

    static SettingsModel fromJson(const QJsonObject& obj) {
        SettingsModel model;
        model.download_folder = obj.value("download_folder").toString();
        model.max_concurrent = obj.value("max_concurrent").toInt(3);
        model.auto_extract = obj.value("auto_extract").toBool();
        model.delete_after = obj.value("delete_after").toBool();
        return model;
    }

    QJsonObject toJson() const {
        QJsonObject obj;
        if (!download_folder.isEmpty()) {
            obj["download_folder"] = download_folder;
        }
        obj["max_concurrent"] = max_concurrent;
        obj["auto_extract"] = auto_extract;
        obj["delete_after"] = delete_after;
        return obj;
    }
};

#endif // SETTINGS_MODEL_H
