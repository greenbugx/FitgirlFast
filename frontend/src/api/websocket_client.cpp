#include "websocket_client.h"
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QDebug>

WebsocketClient::WebsocketClient(QObject *parent)
    : QObject(parent)
{
    connect(&m_webSocket, &QWebSocket::connected, this, &WebsocketClient::onConnected);
    connect(&m_webSocket, &QWebSocket::disconnected, this, &WebsocketClient::onDisconnected);
    connect(&m_webSocket, &QWebSocket::textMessageReceived, this, &WebsocketClient::onTextMessageReceived);

    // Setup reconnect timer - 3s
    m_reconnectTimer.setInterval(3000);
    connect(&m_reconnectTimer, &QTimer::timeout, this, &WebsocketClient::onReconnectTimer);
}

WebsocketClient::~WebsocketClient()
{
    m_intendedDisconnect = true;
    m_webSocket.close();
}

void WebsocketClient::connectToServer(const QString& url)
{
    m_url = url;
    m_intendedDisconnect = false;
    qDebug() << "WebsocketClient: Connecting to" << url;
    m_webSocket.open(QUrl(url));
}

void WebsocketClient::disconnectFromServer()
{
    m_intendedDisconnect = true;
    m_reconnectTimer.stop();
    m_webSocket.close();
}

void WebsocketClient::onConnected()
{
    qDebug() << "WebsocketClient: Connected successfully.";
    m_reconnectTimer.stop();
    emit connected();
}

void WebsocketClient::onDisconnected()
{
    qDebug() << "WebsocketClient: Disconnected.";
    emit disconnected();
    
    // Attempt auto-reconnect if it was a drop
    if (!m_intendedDisconnect && !m_reconnectTimer.isActive()) {
        qDebug() << "WebsocketClient: Starting reconnect timer...";
        m_reconnectTimer.start();
    }
}

void WebsocketClient::onReconnectTimer()
{
    if (!m_intendedDisconnect && m_webSocket.state() == QAbstractSocket::UnconnectedState) {
        qDebug() << "WebsocketClient: Attempting reconnect...";
        m_webSocket.open(QUrl(m_url));
    }
}

void WebsocketClient::onTextMessageReceived(const QString &message)
{
    QJsonParseError parseError;
    QJsonDocument doc = QJsonDocument::fromJson(message.toUtf8(), &parseError);

    if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
        qWarning() << "WebsocketClient: Failed to parse JSON message:" << message;
        return;
    }

    QJsonObject obj = doc.object();
    QString eventType = obj.value("event").toString();
    QString id = obj.value("id").toString();

    // Map backend JSON events to strongly typed Qt Signals
    if (eventType == "started") {
        emit downloadStarted(id);
    } else if (eventType == "progress") {
        double progress = obj.value("progress").toDouble();
        qint64 downloaded = static_cast<qint64>(obj.value("downloaded").toDouble());
        qint64 total = static_cast<qint64>(obj.value("total").toDouble());
        double speed = obj.value("speed").toDouble();
        double eta = obj.value("eta").toDouble();
        emit downloadProgress(id, progress, downloaded, total, speed, eta);
    } else if (eventType == "completed") {
        emit downloadCompleted(id);
    } else if (eventType == "failed") {
        QString errorMsg = obj.value("error").toString();
        emit downloadFailed(id, errorMsg);
    } else if (eventType == "cancelled") {
        emit downloadCancelled(id);
    } else if (eventType == "status") {
        QString msg = obj.value("message").toString();
        emit statusMessage(msg);
    } else {
        qDebug() << "WebsocketClient: Unknown event received:" << eventType;
    }
}
