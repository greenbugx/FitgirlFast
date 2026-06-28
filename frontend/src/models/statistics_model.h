#ifndef STATISTICS_MODEL_H
#define STATISTICS_MODEL_H

#include <QJsonObject>

struct StatisticsModel {
    double elapsed = 0.0;
    double total_mb = 0.0;
    double avg_speed = 0.0;
    int done_c = 0;
    int failed_c = 0;
    int pending_c = 0;

    static StatisticsModel fromJson(const QJsonObject& obj) {
        StatisticsModel model;
        model.elapsed = obj.value("elapsed").toDouble();
        model.total_mb = obj.value("total_mb").toDouble();
        model.avg_speed = obj.value("avg_speed").toDouble();
        model.done_c = obj.value("done_c").toInt();
        model.failed_c = obj.value("failed_c").toInt();
        model.pending_c = obj.value("pending_c").toInt();
        return model;
    }
};

#endif // STATISTICS_MODEL_H
