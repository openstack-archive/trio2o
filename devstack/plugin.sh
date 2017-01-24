# Devstack extras script to install Trio2o

# Test if any trio2o services are enabled
# is_trio2o_enabled
function is_trio2o_enabled {
    [[ ,${ENABLED_SERVICES} =~ ,"to-api" ]] && return 0
    return 1
}

# create_trio2o_accounts() - Set up common required trio2o
# service accounts in keystone
# Project               User            Roles
# -------------------------------------------------------------------------
# $SERVICE_TENANT_NAME  trio2o          service

function create_trio2o_accounts {
    if [[ "$ENABLED_SERVICES" =~ "to-api" ]]; then
        create_service_user "trio2o"

        local trio2o_api=$(get_or_create_service "trio2o" \
            "Cascading" "OpenStack Cascading Service")
        get_or_create_endpoint $trio2o_api \
            "$CENTRAL_REGION_NAME" \
            "$SERVICE_PROTOCOL://$TRIO2O_API_HOST:$TRIO2O_API_PORT/v1.0" \
            "$SERVICE_PROTOCOL://$TRIO2O_API_HOST:$TRIO2O_API_PORT/v1.0" \
            "$SERVICE_PROTOCOL://$TRIO2O_API_HOST:$TRIO2O_API_PORT/v1.0"
    fi
}

# create_nova_apigw_accounts() - Set up common required nova_apigw
# work as nova api serice
# service accounts in keystone
# Project               User            Roles
# -----------------------------------------------------------------
# $SERVICE_TENANT_NAME  nova_apigw      service

function create_nova_apigw_accounts {
    if [[ "$ENABLED_SERVICES" =~ "t-ngw" ]]; then
        create_service_user "nova_apigw"

        local trio2o_nova_apigw=$(get_or_create_service "nova" \
            "compute" "Nova Compute Service")

        get_or_create_endpoint $trio2o_nova_apigw \
            "$CENTRAL_REGION_NAME" \
            "$SERVICE_PROTOCOL://$TRIO2O_NOVA_APIGW_HOST:$TRIO2O_NOVA_APIGW_PORT/v2.1/"'$(tenant_id)s' \
            "$SERVICE_PROTOCOL://$TRIO2O_NOVA_APIGW_HOST:$TRIO2O_NOVA_APIGW_PORT/v2.1/"'$(tenant_id)s' \
            "$SERVICE_PROTOCOL://$TRIO2O_NOVA_APIGW_HOST:$TRIO2O_NOVA_APIGW_PORT/v2.1/"'$(tenant_id)s'
    fi
}

# create_cinder_apigw_accounts() - Set up common required cinder_apigw
# work as cinder api serice
# service accounts in keystone
# Project               User            Roles
# ---------------------------------------------------------------------
# $SERVICE_TENANT_NAME  cinder_apigw    service

function create_cinder_apigw_accounts {
    if [[ "$ENABLED_SERVICES" =~ "t-cgw" ]]; then
        create_service_user "cinder_apigw"

        local trio2o_cinder_apigw=$(get_or_create_service "cinder" \
            "volumev2" "Cinder Volume Service")

        get_or_create_endpoint $trio2o_cinder_apigw \
            "$CENTRAL_REGION_NAME" \
            "$SERVICE_PROTOCOL://$TRIO2O_CINDER_APIGW_HOST:$TRIO2O_CINDER_APIGW_PORT/v2/"'$(tenant_id)s' \
            "$SERVICE_PROTOCOL://$TRIO2O_CINDER_APIGW_HOST:$TRIO2O_CINDER_APIGW_PORT/v2/"'$(tenant_id)s' \
            "$SERVICE_PROTOCOL://$TRIO2O_CINDER_APIGW_HOST:$TRIO2O_CINDER_APIGW_PORT/v2/"'$(tenant_id)s'
    fi
}


# common config-file configuration for trio2o services
function remove_old_endpoint_conf {
    local service=$1

    local endpoint_id
    interface_list="public admin internal"
    for interface in $interface_list; do
        endpoint_id=$(openstack endpoint list \
            --service "$service" \
            --interface "$interface" \
            --region "$REGION_NAME" \
            -c ID -f value)
        if [[ -n "$endpoint_id" ]]; then
            # Delete endpoint
            openstack endpoint delete "$endpoint_id"
        fi
    done
}


# create_trio2o_cache_dir() - Set up cache dir for trio2o
function create_trio2o_cache_dir {

    # Delete existing dir
    sudo rm -rf $TRIO2O_AUTH_CACHE_DIR
    sudo mkdir -p $TRIO2O_AUTH_CACHE_DIR
    sudo chown `whoami` $TRIO2O_AUTH_CACHE_DIR
}

# common config-file configuration for trio2o services
function init_common_trio2o_conf {
    local conf_file=$1

    touch $conf_file
    iniset $conf_file DEFAULT debug $ENABLE_DEBUG_LOG_LEVEL
    iniset $conf_file DEFAULT verbose True
    iniset $conf_file DEFAULT use_syslog $SYSLOG
    iniset $conf_file DEFAULT trio2o_db_connection `database_connection_url trio2o`

    iniset $conf_file client admin_username admin
    iniset $conf_file client admin_password $ADMIN_PASSWORD
    iniset $conf_file client admin_tenant demo
    iniset $conf_file client auto_refresh_endpoint True
    iniset $conf_file client top_pod_name $CENTRAL_REGION_NAME

    iniset $conf_file oslo_concurrency lock_path $TRIO2O_STATE_PATH/lock
}

function configure_trio2o_api {

    if is_service_enabled to-api ; then
        echo "Configuring Trio2o API"

        init_common_trio2o_conf $TRIO2O_API_CONF

        setup_colorized_logging $TRIO2O_API_CONF DEFAULT tenant_name

        if is_service_enabled keystone; then

            create_trio2o_cache_dir

            # Configure auth token middleware
            configure_auth_token_middleware $TRIO2O_API_CONF trio2o \
                $TRIO2O_AUTH_CACHE_DIR

        else
            iniset $TRIO2O_API_CONF DEFAULT auth_strategy noauth
        fi
    fi
}

function configure_trio2o_nova_apigw {
    if is_service_enabled t-ngw ; then
        echo "Configuring Trio2o Nova APIGW"

        init_common_trio2o_conf $TRIO2O_NOVA_APIGW_CONF

        setup_colorized_logging $TRIO2O_NOVA_APIGW_CONF DEFAULT tenant_name

        if is_service_enabled keystone; then

            create_trio2o_cache_dir

            # Configure auth token middleware
            configure_auth_token_middleware $TRIO2O_NOVA_APIGW_CONF trio2o \
                $TRIO2O_AUTH_CACHE_DIR

        else
            iniset $TRIO2O_NOVA_APIGW_CONF DEFAULT auth_strategy noauth
        fi

    fi
}

function configure_trio2o_cinder_apigw {
    if is_service_enabled t-cgw ; then
        echo "Configuring Trio2o Cinder APIGW"

        init_common_trio2o_conf $TRIO2O_CINDER_APIGW_CONF

        setup_colorized_logging $TRIO2O_CINDER_APIGW_CONF DEFAULT tenant_name

        if is_service_enabled keystone; then

            create_trio2o_cache_dir

            # Configure auth token middleware
            configure_auth_token_middleware $TRIO2O_CINDER_APIGW_CONF trio2o \
                $TRIO2O_AUTH_CACHE_DIR

        else
            iniset $TRIO2O_CINDER_APIGW_CONF DEFAULT auth_strategy noauth
        fi

    fi
}

function configure_trio2o_xjob {
    if is_service_enabled to-job ; then
        echo "Configuring Trio2o xjob"

        init_common_trio2o_conf $TRIO2O_XJOB_CONF

        setup_colorized_logging $TRIO2O_XJOB_CONF DEFAULT
    fi
}

function move_glance_server {
    local region_name=$1

    remove_old_endpoint_conf "glance"

    get_or_create_service "glance" "image" "Glance Image Service"
    get_or_create_endpoint \
        "image" \
        "$region_name" \
        "$GLANCE_SERVICE_PROTOCOL://$GLANCE_HOSTPORT" \
        "$GLANCE_SERVICE_PROTOCOL://$GLANCE_HOSTPORT" \
        "$GLANCE_SERVICE_PROTOCOL://$GLANCE_HOSTPORT"
}

if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
    echo summary "Trio2o pre-install"
elif [[ "$1" == "stack" && "$2" == "install" ]]; then
    echo_summary "Installing Trio2o"
elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    echo_summary "Configuring Trio2o"

    export NEUTRON_CREATE_INITIAL_NETWORKS=False
    sudo install -d -o $STACK_USER -m 755 $TRIO2O_CONF_DIR

    echo export PYTHONPATH=\$PYTHONPATH:$TRIO2O_DIR >> $RC_DIR/.localrc.auto

    setup_package $TRIO2O_DIR -e

    if [[ "$TRIO2O_START_SERVICES" == "True" ]]; then
        enable_service to-api to-job t-ngw t-cgw

        configure_trio2o_api
        configure_trio2o_nova_apigw
        configure_trio2o_cinder_apigw
        configure_trio2o_xjob
        recreate_database trio2o
        python "$TRIO2O_DIR/cmd/manage.py" "$TRIO2O_API_CONF"
    fi

elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
    echo_summary "Initializing Trio2o Service"

    if is_service_enabled to-api; then

        create_trio2o_accounts

        run_process to-api "python $TRIO2O_API --config-file $TRIO2O_API_CONF"
    fi

    if is_service_enabled t-ngw; then

        create_nova_apigw_accounts

        run_process t-ngw "python $TRIO2O_NOVA_APIGW --config-file $TRIO2O_NOVA_APIGW_CONF"

    fi

    if is_service_enabled t-cgw; then

        create_cinder_apigw_accounts

        run_process t-cgw "python $TRIO2O_CINDER_APIGW --config-file $TRIO2O_CINDER_APIGW_CONF"
    fi

    if is_service_enabled to-job; then

        run_process to-job "python $TRIO2O_XJOB --config-file $TRIO2O_XJOB_CONF"
    fi

    # move glance to central region
    if [[ "$TRIO2O_START_SERVICES" == "True" ]]; then
        move_glance_server $CENTRAL_REGION_NAME
    fi
fi

if [[ "$1" == "unstack" ]]; then

    if is_service_enabled to-api; then
       stop_process to-api
    fi

    if is_service_enabled t-ngw; then
       stop_process t-ngw
    fi

    if is_service_enabled t-cgw; then
       stop_process t-cgw
    fi

    if is_service_enabled to-job; then
       stop_process to-job
    fi
fi
