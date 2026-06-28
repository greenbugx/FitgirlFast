#ifndef API_CLIENT_H
#define API_CLIENT_H

#include <QObject>
#include <QString>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QJsonObject>

class ApiClient : public QObject
{
    Q_OBJECT
public:
    explicit ApiClient(QObject *parent = nullptr);
    ~ApiClient();

    void initialize(const QString& baseUrl);

    QNetworkReply* getDownloads();
    QNetworkReply* postDownloads(const QJsonObject& payload);

    QNetworkReply* getSettings();
    QNetworkReply* postSettings(const QJsonObject& payload);

    QNetworkReply* togglePause(const QString& id);
    QNetworkReply* cancelDownload(const QString& id);
    
    QNetworkReply* togglePauseAll();
    QNetworkReply* cancelAll();

private:
    QString m_baseUrl;
    QNetworkAccessManager *m_networkManager;

    QNetworkRequest createRequest(const QString& endpoint);
};

#endif // API_CLIENT_H
