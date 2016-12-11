# Devstack extras script to install Trio2o

# Test if any trio2o services are enabled
# is_trio2o_enabled
function is_trio2o_enabled {
    [[ ,${ENABLED_SERVICES} =~ ,"t-api" ]] && return 0
    return 1
}

# create_trio2o_accounts() - Set up common required trio2o
# service accounts in keystone
# Project               User            Roles
# -------------------------------------------------------------------------
# $SERVICE_TENANT_NAME  trio2o          service

function create_trio2o_accounts {
    if [[ "$ENABLED_SERVICES" =~ "t-api" ]]; then
        create_service_user "trio2o"

        if [[ "$KEYSTONE_CATALOG_BACKEND" = 'sql' ]]; then
            local trio2o_api=$(get_or_create_service "trio2o" \
                "Cascading" "OpenStack Cascading Service")
            get_or_create_endpoint $trio2o_api \
                "$REGION_NAME" \
                "$SERVICE_PROTOCOL://$TRIO2O_API_HOST:$TRIO2O_API_PORT/v1.0" \
                "$SERVICE_PROTOCOL://$TRIO2O_API_HOST:$TRIO2O_API_PORT/v1.0" \
                "$SERVICE_PROTOCOL://$TRIO2O_API_HOST:$TRIO2O_API_PORT/v1.0"
        fi
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

        if [[ "$KEYSTONE_CATALOG_BACKEND" = 'sql' ]]; then
            local trio2o_nova_apigw=$(get_or_create_service "nova" \
                "compute" "Nova Compute Service")

            remove_old_endpoint_conf $trio2o_nova_apigw

            get_or_create_endpoint $trio2o_nova_apigw \
                "$REGION_NAME" \
                "$SERVICE_PROTOCOL://$TRIO2O_NOVA_APIGW_HOST:$TRIO2O_NOVA_APIGW_PORT/v2.1/"'$(tenant_id)s' \
                "$SERVICE_PROTOCOL://$TRIO2O_NOVA_APIGW_HOST:$TRIO2O_NOVA_APIGW_PORT/v2.1/"'$(tenant_id)s' \
                "$SERVICE_PROTOCOL://$TRIO2O_NOVA_APIGW_HOST:$TRIO2O_NOVA_APIGW_PORT/v2.1/"'$(tenant_id)s'
        fi
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

        if [[ "$KEYSTONE_CATALOG_BACKEND" = 'sql' ]]; then
            local trio2o_cinder_apigw=$(get_or_create_service "cinder" \
                "volumev2" "Cinder Volume Service")

            remove_old_endpoint_conf $trio2o_cinder_apigw

            get_or_create_endpoint $trio2o_cinder_apigw \
                "$REGION_NAME" \
                "$SERVICE_PROTOCOL://$TRIO2O_CINDER_APIGW_HOST:$TRIO2O_CINDER_APIGW_PORT/v2/"'$(tenant_id)s' \
                "$SERVICE_PROTOCOL://$TRIO2O_CINDER_APIGW_HOST:$TRIO2O_CINDER_APIGW_PORT/v2/"'$(tenant_id)s' \
                "$SERVICE_PROTOCOL://$TRIO2O_CINDER_APIGW_HOST:$TRIO2O_CINDER_APIGW_PORT/v2/"'$(tenant_id)s'
        fi
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
    iniset $conf_file client top_pod_name $REGION_NAME

    iniset $conf_file oslo_concurrency lock_path $TRIO2O_STATE_PATH/lock
}

function configure_trio2o_api {

    if is_service_enabled t-api ; then
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
    if is_service_enabled t-job ; then
        echo "Configuring Trio2o xjob"

        init_common_trio2o_conf $TRIO2O_XJOB_CONF

        setup_colorized_logging $TRIO2O_XJOB_CONF DEFAULT
    fi
}

function move_neutron_server {
    local region_name=$1

    remove_old_endpoint_conf "neutron"

    get_or_create_service "neutron" "network" "Neutron Service"
    get_or_create_endpoint "network" \
        "$region_name" \
        "$Q_PROTOCOL://$SERVICE_HOST:$Q_PORT/" \
        "$Q_PROTOCOL://$SERVICE_HOST:$Q_PORT/" \
        "$Q_PROTOCOL://$SERVICE_HOST:$Q_PORT/"

    iniset $NEUTRON_CONF nova region_name $region_name

    stop_process q-svc
    # remove previous failure flag file since we are going to restart service
    rm -f "$SERVICE_DIR/$SCREEN_NAME"/q-svc.failure
    sleep 20
    run_process q-svc "$NEUTRON_BIN_DIR/neutron-server --config-file $NEUTRON_CONF --config-file /$Q_PLUGIN_CONF_FILE"
}

# if the plugin is enabled to run, that means the TRIO2O is
# enabled by default
export Q_ENABLE_TRIO2O=True

   if   [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        echo summary "Trio2o pre-install"
   elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing Trio2o"
   elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
       echo_summary "Configuring Trio2o"
       export NEUTRON_CREATE_INITIAL_NETWORKS=False
       sudo install -d -o $STACK_USER -m 755 $TRIO2O_CONF_DIR

       enable_service t-api t-job t-ngw t-cgw

       configure_trio2o_api
       configure_trio2o_nova_apigw
       configure_trio2o_cinder_apigw
       configure_trio2o_xjob

       echo export PYTHONPATH=\$PYTHONPATH:$TRIO2O_DIR >> $RC_DIR/.localrc.auto

       setup_package $TRIO2O_DIR -e

       recreate_database trio2o
       python "$TRIO2O_DIR/cmd/manage.py" "$TRIO2O_API_CONF"

   elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
       echo_summary "Initializing Trio2o Service"

       if  is_service_enabled t-api; then

           create_trio2o_accounts

           run_process t-api "python $TRIO2O_API --config-file $TRIO2O_API_CONF"
       fi

       if  is_service_enabled t-ngw; then

           create_nova_apigw_accounts

           run_process t-ngw "python $TRIO2O_NOVA_APIGW --config-file $TRIO2O_NOVA_APIGW_CONF"

           # Nova services are running, but we need to re-configure them to
           # move them to bottom region
           iniset $NOVA_CONF neutron region_name $POD_REGION_NAME
           iniset $NOVA_CONF neutron url "$Q_PROTOCOL://$SERVICE_HOST:$Q_PORT"
           iniset $NOVA_CONF cinder os_region_name $POD_REGION_NAME

           get_or_create_endpoint "compute" \
               "$POD_REGION_NAME" \
               "$NOVA_SERVICE_PROTOCOL://$NOVA_SERVICE_HOST:$NOVA_SERVICE_PORT/v2.1/"'$(tenant_id)s' \
               "$NOVA_SERVICE_PROTOCOL://$NOVA_SERVICE_HOST:$NOVA_SERVICE_PORT/v2.1/"'$(tenant_id)s' \
               "$NOVA_SERVICE_PROTOCOL://$NOVA_SERVICE_HOST:$NOVA_SERVICE_PORT/v2.1/"'$(tenant_id)s'

           stop_process n-api
           stop_process n-cpu
           # remove previous failure flag file since we are going to restart service
           rm -f "$SERVICE_DIR/$SCREEN_NAME"/n-api.failure
           rm -f "$SERVICE_DIR/$SCREEN_NAME"/n-cpu.failure
           sleep 20
           run_process n-api "$NOVA_BIN_DIR/nova-api"
           run_process n-cpu "$NOVA_BIN_DIR/nova-compute --config-file $NOVA_CONF" $LIBVIRT_GROUP
       fi

       if is_service_enabled q-svc; then
           move_neutron_server $POD_REGION_NAME
       fi

       if is_service_enabled t-cgw; then

           create_cinder_apigw_accounts

           run_process t-cgw "python $TRIO2O_CINDER_APIGW --config-file $TRIO2O_CINDER_APIGW_CONF"

           get_or_create_endpoint "volumev2" \
               "$POD_REGION_NAME" \
               "$CINDER_SERVICE_PROTOCOL://$CINDER_SERVICE_HOST:$CINDER_SERVICE_PORT/v2/"'$(tenant_id)s' \
               "$CINDER_SERVICE_PROTOCOL://$CINDER_SERVICE_HOST:$CINDER_SERVICE_PORT/v2/"'$(tenant_id)s' \
               "$CINDER_SERVICE_PROTOCOL://$CINDER_SERVICE_HOST:$CINDER_SERVICE_PORT/v2/"'$(tenant_id)s'
       fi

       if is_service_enabled t-job; then

          run_process t-job "python $TRIO2O_XJOB --config-file $TRIO2O_XJOB_CONF"
       fi
   fi

   if  [[ "$1" == "unstack" ]]; then

       if is_service_enabled t-api; then
          stop_process t-api
       fi

       if is_service_enabled t-ngw; then
          stop_process t-ngw
       fi

       if is_service_enabled t-cgw; then
          stop_process t-cgw
       fi

       if is_service_enabled t-job; then
          stop_process t-job
       fi
   fi