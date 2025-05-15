CREATE SCHEMA IF NOT EXISTS app_data;

DROP TABLE IF EXISTS app_data.product_images CASCADE;
DROP TABLE IF EXISTS app_data.products CASCADE;
DROP TABLE IF EXISTS app_data.categories CASCADE;

CREATE TABLE app_data.categories (
  category_id SERIAL PRIMARY KEY,
  name VARCHAR(50),
  background_url VARCHAR(255),
  type INT,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE app_data.products (
  product_id SERIAL PRIMARY KEY,
  category_id INT REFERENCES app_data.categories(category_id),
  code VARCHAR(10),
  name VARCHAR(50) UNIQUE NOT NULL,
  description TEXT,
  brand VARCHAR(50),
  discount_percentage INT DEFAULT 0,
  unit_price JSON,
  total_orders INT DEFAULT 0,
  total_ratings INT DEFAULT 0,
  overall_stars REAL,
  stock_quantity INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE app_data.product_images (
  product_image_id SERIAL PRIMARY KEY,
  product_id INT REFERENCES app_data.products(product_id),
  image_name VARCHAR(100),
  image_url VARCHAR(255),
  image_type SMALLINT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE app_data.migrations (
    id integer NOT NULL,
    migration character varying(255) NOT NULL,
    batch integer NOT NULL
);

CREATE SEQUENCE app_data.migrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE app_data.migrations_id_seq OWNED BY app_data.migrations.id;

CREATE TABLE app_data.otp (
    phone_number character varying(255) NOT NULL,
    code character varying(255) NOT NULL,
    verified_at timestamp(0) without time zone,
    created_at timestamp(0) without time zone,
    updated_at timestamp(0) without time zone
);

CREATE TABLE app_data.password_resets (
    token character varying(255) NOT NULL,
    created_at timestamp(0) without time zone,
    updated_at timestamp(0) without time zone
);


CREATE TABLE app_data.personal_access_tokens (
    id bigint NOT NULL,
    tokenable_type character varying(255) NOT NULL,
    tokenable_id bigint NOT NULL,
    name character varying(255) NOT NULL,
    token character varying(64) NOT NULL,
    abilities text,
    last_used_at timestamp(0) without time zone,
    expires_at timestamp(0) without time zone,
    created_at timestamp(0) without time zone,
    updated_at timestamp(0) without time zone
);

CREATE SEQUENCE app_data.personal_access_tokens_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE app_data.personal_access_tokens_id_seq OWNED BY app_data.personal_access_tokens.id;

CREATE TABLE app_data.sessions (
    id character varying(255) NOT NULL,
    user_id bigint,
    ip_address character varying(45),
    user_agent text,
    payload text NOT NULL,
    last_activity integer NOT NULL
);

CREATE TABLE app_data.user_addresses (
    user_address_id bigint NOT NULL,
    urban_name character varying(255) NOT NULL,
    suburb_name character varying(255) NOT NULL,
    quarter_name character varying(255),
    full_address character varying(255) NOT NULL,
    is_default_address boolean DEFAULT false NOT NULL,
    user_id bigint NOT NULL,
    created_at timestamp(0) without time zone,
    updated_at timestamp(0) without time zone
);

CREATE SEQUENCE app_data.user_addresses_user_address_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE app_data.user_addresses_user_address_id_seq OWNED BY app_data.user_addresses.user_address_id;

CREATE TABLE app_data.users (
    user_id bigint NOT NULL,
    name character varying(50) NOT NULL,
    email character varying(255) NOT NULL,
    phone_verified_at timestamp(0) without time zone,
    password character varying(255) NOT NULL,
    phone_number character varying(10) NOT NULL,
    urban character varying(255),
    suburb character varying(255),
    quarter character varying(255),
    address character varying(255),
    cart_id integer,
    avatar text,
    gender character varying(4),
    date_of_birth date,
    role_type smallint DEFAULT '0'::smallint NOT NULL,
    remember_token character varying(100),
    created_at timestamp(0) without time zone,
    updated_at timestamp(0) without time zone
);

CREATE SEQUENCE app_data.users_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE app_data.users_user_id_seq OWNED BY app_data.users.user_id;

ALTER TABLE ONLY app_data.migrations ALTER COLUMN id SET DEFAULT nextval('app_data.migrations_id_seq'::regclass);

ALTER TABLE ONLY app_data.personal_access_tokens ALTER COLUMN id SET DEFAULT nextval('app_data.personal_access_tokens_id_seq'::regclass);


ALTER TABLE ONLY app_data.user_addresses ALTER COLUMN user_address_id SET DEFAULT nextval('app_data.user_addresses_user_address_id_seq'::regclass);

ALTER TABLE ONLY app_data.users ALTER COLUMN user_id SET DEFAULT nextval('app_data.users_user_id_seq'::regclass);

ALTER TABLE ONLY app_data.migrations
    ADD CONSTRAINT migrations_pkey PRIMARY KEY (id);

ALTER TABLE ONLY app_data.otp
    ADD CONSTRAINT otp_phone_number_unique UNIQUE (phone_number);

ALTER TABLE ONLY app_data.otp
    ADD CONSTRAINT otp_pkey PRIMARY KEY (phone_number);

ALTER TABLE ONLY app_data.password_resets
    ADD CONSTRAINT password_resets_pkey PRIMARY KEY (token);

ALTER TABLE ONLY app_data.password_resets
    ADD CONSTRAINT password_resets_token_unique UNIQUE (token);

ALTER TABLE ONLY app_data.personal_access_tokens
    ADD CONSTRAINT personal_access_tokens_pkey PRIMARY KEY (id);

ALTER TABLE ONLY app_data.personal_access_tokens
    ADD CONSTRAINT personal_access_tokens_token_unique UNIQUE (token);

ALTER TABLE ONLY app_data.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY app_data.user_addresses
    ADD CONSTRAINT user_addresses_pkey PRIMARY KEY (user_address_id);

ALTER TABLE ONLY app_data.users
    ADD CONSTRAINT users_email_unique UNIQUE (email);

ALTER TABLE ONLY app_data.users
    ADD CONSTRAINT users_phone_number_unique UNIQUE (phone_number);

ALTER TABLE ONLY app_data.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);

CREATE INDEX personal_access_tokens_tokenable_type_tokenable_id_index ON app_data.personal_access_tokens USING btree (tokenable_type, tokenable_id);

CREATE INDEX sessions_last_activity_index ON app_data.sessions USING btree (last_activity);

CREATE INDEX sessions_user_id_index ON app_data.sessions USING btree (user_id);


CREATE INDEX users_cart_id_index ON app_data.users USING btree (cart_id);

ALTER TABLE ONLY app_data.user_addresses
    ADD CONSTRAINT user_addresses_user_id_foreign FOREIGN KEY (user_id) REFERENCES app_data.users(user_id) ON DELETE CASCADE;
