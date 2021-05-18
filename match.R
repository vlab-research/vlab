library(readr)
library(dplyr)
library(Matching)

pairup <- function (a) {
    N <- length(a)
    if (N %% 2 != 0) {
        stop('pairup needs an even-length vector')
    }
    out <- matrix(0, N/2, 2)
    for (i in 1:nrow(out)) {
        out[i,] <- a[1:2]
        a <- a[3:length(a)]
    }
    out
}

get_order <- function (m) {
    pca <- prcomp(scale(m))$x
    order(pca[, "PC1"])
}

pair <- function (di, blacklist) {
    s <- order(di)[2:length(di)]
    for (i in s) {
        if (!(i %in% blacklist)) {
            return(i)
        }
    }
}

pairem <- function (ma, or) {
    dists <- as.matrix(dist(scale(ma), method='euclidean'))
    pairs <- c()
    while(length(or) > 0) {
        i <- or[1]
        d <- dists[i, ]
        p <- pair(d, pairs)
        pairs <- append(pairs, c(i, p))
        or <- or[(or != p) & (or != i)]
    }
    pairs
}

flip <- function () {
    a <- rbinom(1, 1, 0.5)
    b <- ifelse(a == 0, 1, 0)
    c(a,b)
}

choose <- function(pairs) {
    # pairs is a vector where index 1 and index 2 are
    # a pair, same with index 3 and 4, etc...
    N <- length(pairs)
    out <- rep(0, N)
    for (i in seq(1, N, by=2)) {
        f <- flip()
        a <- pairs[i]
        b <- pairs[i+1]
        out[a] <- f[1]
        out[b] <- f[2]
    }
    out
}

get_balance <- function(formula, dat, labels, print.level=0) {
    dat <- mutate(dat, a = labels)
    MatchBalance(formula,
                 data=dat,
                 print.level=print.level)
}


above_threshes <- function (balance, threshes) {
    bm <- balance$BeforeMatching
    for (i in 1:length(bm)) {
        thresh <- threshes[i]
        if (is.na(thresh)) {
            stop("Not enough thresholds given!")
        }
        val <- bm[[i]]$tt$p.value
        if (val < thresh) {
            return(FALSE)
        }
    }
    TRUE
}

rerandomize <- function (formula, df, gen_assignment, balance_on, threshes, minimum_threshold, iters) {
    for (i in 1:iters) {
        labels <- gen_assignment(df)
        balance <- get_balance(formula, df, labels)
        mi <- balance$BMsmallest.p.value

        if ((mi > minimum_threshold) & above_threshes(balance, threshes)) {
            print(balance)
            return(labels)
        }
    }
}

match_and_rerandomize <- function (formula, ma, balance_on, threshes, minimum_threshold, iters) {
    selected_ma <- dplyr::select(ma, all_of(balance_on))
    or <- get_order(selected_ma)
    pairs  <- pairem(selected_ma, or)
    gen_assignment <- function(df) choose(pairs)

    assignment <- rerandomize(formula, ma, gen_assignment, balance_on, threshes, minimum_threshold, iters)

    list(assignment = assignment, pairs = pairs)
}

check_unique <- function (X) {
    N <- ncol(X)
    for (i in 1:(N-1)) {
        for (j in (i+1):N) {
            if (all(X[,i] == X[,j])) {
                print('phooey')
            }
        }
    }
}

make_pair_ids <- function (pairs) {
    N <- length(pairs)
    out <- rep(0, N)
    j <- 1
    for (i in seq(1, N, by=2)) {
        a <- pairs[i]
        b <- pairs[i+1]
        out[a] <- j
        out[b] <- j
        j <- j + 1
    }
    out
}

#################################
# Original assignmnet
raw_ma <- read_csv('outs/ma.csv')
ma <- dplyr::select(raw_ma, -disthash)
balance_on <- c('kutchas', 'university', 'malaria', 'malaria_now', 'population', 'cost_per_completion', 'saturated')
thresholds <-  c(c(.6, .3, .3, .6, .75, .75, .3), rep(.1, 13))
## thresholds <- rep(.05, 20)
formula <- a ~ kutchas + university + unemployed + malaria + malaria_now + population + cost_per_completion + saturated + under_net + exclusion + audienced + current_total + cost_per_message + CTR + CPM + I(malaria**2) + I(malaria_now**2) + log(population) + I(kutchas*population) + I(malaria*kutchas)



res <- match_and_rerandomize(formula, ma, balance_on, thresholds, 0.1, 100)

## write_csv(mutate(raw_ma, treatment=bl6), 'outs/ma-with-treatment.csv')
write_csv(mutate(raw_ma, pair_id=make_pair_ids(res$pairs)), 'outs/ma-with-pair-id.csv')



###############################################
# For exact p-values
library(doRNG)
cl <- parallel::makeForkCluster(7)
doParallel::registerDoParallel(cl)

formula <- a ~ kutchas + university + unemployed + malaria + malaria_now + population + cost_per_completion + cost_per_message + CTR + CPM + I(malaria**2) + I(malaria_now**2) + I(kutchas*population) + I(malaria*kutchas)

set.seed(123)
bb <- foreach(i = 1:1000, .combine = 'cbind') %dorng% {
    match_and_rerandomize(formula, ma, balance_on, thresholds, 0.35, 2000)$assignment
}

write_csv(data.frame(bb), 'outs/cluster-assignments-2.csv')


ma <- read_csv('outs/ma-with-treatment.csv')
b <- get_balance(formula, ma, ma$treatment, 1)

###############################
# Checking balance

individual <- read_csv('outs/individual-with-treatment.csv')
individual <- read_csv('outs/individual-for-balance.csv')

MatchBalance(treatment ~ kutcha + pucca + university + unemployed + malaria + malaria_now + under_net, data=individual)


ddb <- read_csv('outs/mnm-ddb-clean.csv') %>%
    mutate(kutcha = dwelling == "Kutcha (made of mud, tin, straw)",
           pucca = dwelling == "Pucca (have cement/brick wall and floor",
           university = education == "University degree or higher",
           unemployed = occupation == "Unemployed")

MatchBalance(treatment ~ kutcha + pucca + university + unemployed, data=ddb)



########################################
# INDIVIDUAL EFFECT STUDY
ind_effect <- read_csv('outs/ind-effect-for-balance.csv')

balance_on <- c('treatment', 'gender', 'dwelling', 'education', 'malaria4months', 'fever4months', 'hasmosquitonet', 'caste')
thresholds  <- rep(0.2, 18)
formula <- a ~ treatment + gender + dwelling + education + malaria4months + fever4months + hasmosquitonet + caste
gen <- function (df) rbinom(nrow(df), 1, 0.5)
b <- rerandomize(formula, ind_effect, gen, balance_on, thresholds, 0.2, 100)


balance <- MatchBalance(formula, data=ind_effect %>% mutate(a = b))
