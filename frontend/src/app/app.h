#ifndef APP_H
#define APP_H

#include <QObject>
#include <QMainWindow>
#include <memory>

class ApiClient;
class WebsocketClient;
class QNetworkReply;

class App : public QObject
{
    Q_OBJECT
public:
    explicit App(QObject *parent = nullptr);
    ~App();

    void initialize();

private slots:
    void testGetSettingsFinished();
    void testPostDownloadFinished();

private:
    std::unique_ptr<QMainWindow> m_mainWindow;
    std::unique_ptr<ApiClient> m_apiClient;
    std::unique_ptr<WebsocketClient> m_wsClient;
    
    QNetworkReply* m_settingsReply = nullptr;
    QNetworkReply* m_downloadReply = nullptr;
};

#endif // APP_H
