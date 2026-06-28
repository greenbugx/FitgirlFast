cmake_minimum_required(VERSION 3.16)

project(Fetchra VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Network WebSockets)

set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

set(PROJECT_SOURCES
    src/main.cpp
    src/app/app.cpp
    src/app/app.h
    src/api/api_client.cpp
    src/api/api_client.h
    src/api/websocket_client.cpp
    src/api/websocket_client.h
)

add_executable(Fetchra
    ${PROJECT_SOURCES}
)

target_link_libraries(Fetchra PRIVATE 
    Qt6::Core 
    Qt6::Gui 
    Qt6::Widgets
    Qt6::Network
    Qt6::WebSockets
)

# Set the include directories
target_include_directories(Fetchra PRIVATE src)
