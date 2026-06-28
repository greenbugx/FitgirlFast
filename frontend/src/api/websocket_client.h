#ifndef WEBSOCKET_CLIENT_H
#define WEBSOCKET_CLIENT_H

#include <QObject>
#include <QString>
#include <QWebSocket>
#include <QTimer>

class WebsocketClient : public QObject
{
    Q_OBJECT
public:
    explicit WebsocketClient(QObject *parent = nullptr);
    ~WebsocketClient();

    void connectToServer(const QString& url);
    void disconnectFromServer();

signals:
    void connected();
    void disconnected();
    
    // Parsed strongly-typed events
    void downloadStarted(const QString& id);
    void downloadProgress(const QString& id, double progress, qint64 downloaded, qint64 total, double speed, double eta);
    void downloadCompleted(const QString& id);
    void downloadFailed(const QString& id, const QString& error);
    void downloadCancelled(const QString& id);
    void statusMessage(const QString& message);

private slots:
    void onConnected();
    void onDisconnected();
    void onTextMessageReceived(const QString &message);
    void onReconnectTimer();

private:
    QWebSocket m_webSocket;
    QString m_url;
    QTimer m_reconnectTimer;
    bool m_intendedDisconnect = false;
};

#endif // WEBSOCKET_CLIENT_H
