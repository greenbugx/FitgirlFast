#include "api_client.h"
#include <QNetworkRequest>
#include <QJsonDocument>
#include <QUrl>

ApiClient::ApiClient(QObject *parent)
    : QObject(parent),
      m_networkManager(new QNetworkAccessManager(this))
{
}

ApiClient::~ApiClient() = default;

void ApiClient::initialize(const QString& baseUrl)
{
    m_baseUrl = baseUrl;
}

QNetworkRequest ApiClient::createRequest(const QString& endpoint)
{
    QUrl url(m_baseUrl + endpoint);
    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    return request;
}

QNetworkReply* ApiClient::getDownloads()
{
    return m_networkManager->get(createRequest("/downloads"));
}

QNetworkReply* ApiClient::postDownloads(const QJsonObject& payload)
{
    QJsonDocument doc(payload);
    return m_networkManager->post(createRequest("/downloads"), doc.toJson(QJsonDocument::Compact));
}

QNetworkReply* ApiClient::getSettings()
{
    return m_networkManager->get(createRequest("/settings"));
}

QNetworkReply* ApiClient::postSettings(const QJsonObject& payload)
{
    QJsonDocument doc(payload);
    return m_networkManager->post(createRequest("/settings"), doc.toJson(QJsonDocument::Compact));
}

QNetworkReply* ApiClient::togglePause(const QString& id)
{
    return m_networkManager->post(createRequest(QString("/downloads/pause/%1").arg(id)), QByteArray());
}

QNetworkReply* ApiClient::cancelDownload(const QString& id)
{
    return m_networkManager->post(createRequest(QString("/downloads/cancel/%1").arg(id)), QByteArray());
}

QNetworkReply* ApiClient::togglePauseAll()
{
    return m_networkManager->post(createRequest("/downloads/pause"), QByteArray());
}

QNetworkReply* ApiClient::cancelAll()
{
    return m_networkManager->post(createRequest("/downloads/cancel"), QByteArray());
}
