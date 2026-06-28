#include "app.h"
#include "api/api_client.h"
#include "api/websocket_client.h"
#include <QMainWindow>
#include <QVBoxLayout>
#include <QLabel>
#include <QWidget>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QDebug>
#include <QTimer>

App::App(QObject *parent)
    : QObject(parent),
      m_mainWindow(std::make_unique<QMainWindow>()),
      m_apiClient(std::make_unique<ApiClient>()),
      m_wsClient(std::make_unique<WebsocketClient>())
{
    m_mainWindow->setWindowTitle("Fetchra - Initializing...");
    m_mainWindow->resize(800, 600);

    QWidget *centralWidget = new QWidget(m_mainWindow.get());
    QVBoxLayout *layout = new QVBoxLayout(centralWidget);
    
    QLabel *label = new QLabel("Fetchra Qt6 Frontend - Pipeline Testing", centralWidget);
    label->setAlignment(Qt::AlignCenter);
    layout->addWidget(label);
    
    m_mainWindow->setCentralWidget(centralWidget);
}

App::~App() = default;

void App::initialize()
{
    qDebug() << "--- Initializing App ---";
    m_apiClient->initialize("http://127.0.0.1:8000");
    
    // Connect WebSocket
    connect(m_wsClient.get(), &WebsocketClient::connected, this, [](){
        qDebug() << "[WS] Connected to Server";
    });
    connect(m_wsClient.get(), &WebsocketClient::downloadProgress, this, [](const QString& id, double progress, qint64 down, qint64 total, double speed, double eta) {
        qDebug() << "[WS] Progress -> ID:" << id << "Pct:" << progress << "% Speed:" << speed;
    });
    connect(m_wsClient.get(), &WebsocketClient::downloadCompleted, this, [](const QString& id) {
        qDebug() << "[WS] Completed -> ID:" << id;
    });
    connect(m_wsClient.get(), &WebsocketClient::downloadFailed, this, [](const QString& id, const QString& error) {
        qDebug() << "[WS] Failed -> ID:" << id << "Error:" << error;
    });
    
    m_wsClient->connectToServer("ws://127.0.0.1:8000/ws");

    // Test GET /settings
    QTimer::singleShot(500, this, [this]() {
        qDebug() << "--- Sending GET /settings ---";
        m_settingsReply = m_apiClient->getSettings();
        connect(m_settingsReply, &QNetworkReply::finished, this, &App::testGetSettingsFinished);
    });

    // Test POST /downloads
    QTimer::singleShot(1000, this, [this]() {
        qDebug() << "--- Sending POST /downloads ---";
        QJsonObject item;
        item["type"] = "http";
        item["url"] = "http://speedtest.tele2.net/1MB.zip"; // Fast small file
        QJsonArray items;
        items.append(item);
        
        QJsonObject payload;
        payload["items"] = items;
        
        m_downloadReply = m_apiClient->postDownloads(payload);
        connect(m_downloadReply, &QNetworkReply::finished, this, &App::testPostDownloadFinished);
    });
    
    m_mainWindow->show();
}

void App::testGetSettingsFinished()
{
    if (m_settingsReply->error() == QNetworkReply::NoError) {
        QString response = m_settingsReply->readAll();
        qDebug() << "[API] GET /settings Success:" << response;
    } else {
        qDebug() << "[API] GET /settings Failed:" << m_settingsReply->errorString();
    }
    m_settingsReply->deleteLater();
}

void App::testPostDownloadFinished()
{
    if (m_downloadReply->error() == QNetworkReply::NoError) {
        QString response = m_downloadReply->readAll();
        qDebug() << "[API] POST /downloads Success:" << response;
    } else {
        qDebug() << "[API] POST /downloads Failed:" << m_downloadReply->errorString();
    }
    m_downloadReply->deleteLater();
}
